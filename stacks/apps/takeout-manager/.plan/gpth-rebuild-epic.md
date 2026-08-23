# Epic — Takeout Manager: GPTH extraction, archive visibility & conflict control

## Goal
Everything driven from the takeout-manager app — no manual SSH/scripts. Make GPTH the
authoritative extraction (deduped, EXIF-dated, collision-safe), let users see and
inspect archives, rebuild the library on demand, and control conflict handling —
while keeping today's features (cookie updates, download tracking, progress).

## Decisions (locked)
- **immich stays manual.** User deletes + recreates the Google-Photos external library
  in immich (uploads untouched); app does not call immich.
- **Full GPTH date structure** as the library layout (drop the flat `pictures/`+`videos/`
  split). GPTH flags today: `--albums nothing --write-exif --divide-to-dates 2`.
- **Rebuild = clear-first, then one cross-export GPTH pass.** Numbers (Aug 2026): 1.2 TB
  free + 324 GB freed by clearing = ~1.52 TB; peak (raw ~750 GB + deduped output ~350 GB)
  ≈ 1.2 TB → fits. Feature must guard on free space before starting.
- **Archives are the backup of record**; extraction never deletes them.
- Backup-level dedup (Kopia) only works on decompressed content, not `.tgz` — noted for
  the separate backup discussion; not part of this epic.

## Stories (INVEST; sticky-note + acceptance criteria)

### B — See existing archives  *(P1, first slice)*
See every archive on disk with size, export date, and download/extract status.
- Given `google_photos_takeout`, When I open Archives, Then each archive shows size,
  export timestamp, and status reconciled with the DB.

### A — Download and extraction are separate  *(P1)*
Model: an **archive** is first-class (a file on disk); a **download** is one task that
produces archives; **extraction** is independent and works on any archive.

**A1 — Extract any archive.** From the Archives view, extract any archive whether the
app downloaded it or not.
- Given an archive on disk (including a `disk` orphan), When I trigger Extract, Then an
  extract task is queued for that archive by filename — no download, no job required.
- Needs a worker extract-by-filename path (today `extract_chunk` reconstructs the name
  from timestamp+chunk_index, so it can't handle arbitrary/orphan names).

**A2 — Optional extract-after-download.** When creating a download, choose whether to
auto-extract each chunk as it lands.
- Given I create a download with "extract after download" on, When a chunk finishes
  downloading, Then it is queued for extraction; with it off, chunks stop at downloaded.

### D — GPTH is the authoritative extraction  *(P0 correctness)* — approach (ii)
GPTH is the *only* extraction. Drop the per-chunk naive `extract` phase entirely; a
single job-level GPTH pass over the whole export does the extraction (dedup, EXIF,
date folders).
- Given all chunks of a job are downloaded and auto-extract is on, When downloads
  complete, Then one GPTH pass runs over the whole export and the job completes when it
  finishes; there is no per-chunk `extract` task and no flatten-by-basename.
- Given auto-extract is off, When downloads complete, Then the job completes with no GPTH.

State-machine change:
- Chunk lifecycle ends at `downloaded` (remove per-chunk `pending_extraction`/`extracted`
  from the flow); the GPTH pass is triggered when all chunks are `downloaded`.
- Job `completed` now means the GPTH pass finished (not "all chunks extracted").
- Retire `DownloadService.extract_chunk` + the daemon `extract` branch + the
  `get_next_downloaded`→`extract` dispatch.

Open (confirm before coding): (1) route A1's manual extract-any-archive through GPTH
too? (2) keep the task type name `metadata`, or rename to `extract`/`gpth` now that it
is the extraction?

### F — Rebuild library from existing archives  *(P0 unblocks)*
Wipe the extracted library and regenerate it from archives, from the UI.
- Given archives exist and free space passes the guard, When I trigger Rebuild, Then the
  extracted tree is cleared and regenerated via a single cross-export GPTH pass, with a
  warning that immich must re-scan.

### C — Archive timeline & overlap preview  *(P2)*
Peek into an archive: photo date-spread (years, months) and overlap with other archives.
- Given an archive, When I request its timeline, Then I see per-year (and month) counts
  and overlap flags. Content scan is expensive → background job, cached per archive.

### E — Configurable conflict handling  *(P2)*
Choose how name/content conflicts resolve and see what conflicted.
- Given a conflict, When policy is X (skip-if-identical / keep-both / overwrite), Then the
  worker applies X and reports it.

### G — Existing features preserved  *(cross-cutting)*
Cookie updates, download tracking, progress keep working — regression tests.

## Sequencing (reprioritized 2026-08-17)
1. B (archives view) ✅ → 2. A (decoupled extract) → 3. D (GPTH authoritative) →
4. C (timeline) → 5. E (conflicts) → 6. **F (rebuild) — absolute last**, since it's
the destructive wipe-and-rebuild and should only run once everything else is trusted.

## Method (per dev guidelines)
Outside-in TDD: each story starts with a failing integration test defining the
API/worker contract, then unit tests. Mock only owned abstractions (repos, runners),
never 3rd-party/system deps directly.

## Open / to refine
- Story B: does "status" come from the DB only, or reconcile DB + on-disk listing
  (archives downloaded manually pre-app won't be in the DB)?
- Story C: date source — filename patterns (PXL_/IMG_) vs tar header mtime vs JSON
  `photoTakenTime`. JSON is truest but requires reading sidecars.
- Story F: how to represent progress/rollback if a rebuild fails partway.
