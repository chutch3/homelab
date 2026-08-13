#!/usr/bin/env bash
# Copy the gamarr ROM library onto a removable SD card.
#
# The card is identified by its FILESYSTEM LABEL, not a device path (/dev/sdb1
# shuffles) or a mountpoint (varies by OS/user). Label the card once, then just
# plug it in and run this — the script finds wherever it's mounted.
#
#   Label a card:   sudo fatlabel /dev/sdX1 GAMESSD     (FAT/exFAT)
#                   sudo e2label  /dev/sdX1 GAMESSD     (ext4)
#
#   Run:            ./sync-roms-to-sdcard.sh                  # uses SDCARD_LABEL / default
#                   ./sync-roms-to-sdcard.sh -l MYCARD        # pick card by label
#                   ./sync-roms-to-sdcard.sh -d /media/me/X   # or an explicit path
#                   ./sync-roms-to-sdcard.sh --list           # show removable devices + labels
#                   ./sync-roms-to-sdcard.sh -n               # dry run (show what would copy)
#
set -euo pipefail

# --- Defaults (override via flags or .env) -----------------------------------
SDCARD_LABEL="${SDCARD_LABEL:-GAMESSD}"   # filesystem label of the target card
DEST_SUBDIR="${DEST_SUBDIR:-Emulation/roms}"  # on-card folder; EmuDeck's layout. Non-EmuDeck: -s roms (or -s "")
GAMES_ROMS_SRC="${GAMES_ROMS_SRC:-}"      # pre-mounted roms path; empty => mount the NAS share
DEST_PATH=""
DRY_RUN=0
MIRROR=0
DID_AUTOMOUNT=0                           # set if we udisksctl-mounted the card ourselves

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/.env}"

log()  { printf '[sync-roms] %s\n' "$*"; }
die()  { printf '[sync-roms] ERROR: %s\n' "$*" >&2; exit 1; }

usage() { awk 'NR>1 && /^#/{sub(/^# ?/,"");print;next} NR>1{exit}' "${BASH_SOURCE[0]}"; exit "${1:-0}"; }

# Mountpoint of a mounted filesystem by label (empty if not mounted).
label_mount() { findmnt -rno TARGET "LABEL=$1" 2>/dev/null | head -1; }

# Device node of an attached partition by label (empty if not present).
label_dev() { lsblk -rno PATH,LABEL | awk -v l="$1" '$2==l{print $1; exit}'; }

# Read a single KEY=value from the .env without sourcing the whole file, so a
# space/backtick/$() in some unrelated secret can't abort us or leak into scope.
env_get() {
    local key="$1" val
    val="$(grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | tail -1)" || true
    val="${val#*=}"
    val="${val%\"}"; val="${val#\"}"   # strip optional surrounding quotes
    val="${val%\'}"; val="${val#\'}"
    printf '%s' "$val"
}

list_removable() {
    log "Attached block devices (removable = RM 1):"
    # -P key="value" pairs parse reliably even when LABEL/FSTYPE are empty,
    # unlike column-position parsing of the aligned default output. NAME (not
    # PATH) is used so eval can't clobber the shell's $PATH.
    lsblk -P -o NAME,LABEL,FSTYPE,SIZE,RM,MOUNTPOINT | while read -r line; do
        eval "$line"
        [ "${RM:-0}" = "1" ] || continue
        printf '  %-14s label=%-16s fstype=%-6s size=%-8s %s\n' \
            "/dev/$NAME" "${LABEL:-–}" "${FSTYPE:-–}" "$SIZE" "${MOUNTPOINT:-(not mounted)}"
    done
    exit 0
}

# --- Parse args --------------------------------------------------------------
while [ $# -gt 0 ]; do
    case "$1" in
        -l|--label)       SDCARD_LABEL="${2:?}"; shift 2 ;;
        -d|--dest)        DEST_PATH="${2:?}";    shift 2 ;;
        -s|--dest-subdir) DEST_SUBDIR="${2?}";   shift 2 ;;
        -n|--dry-run)     DRY_RUN=1; shift ;;
        --mirror)         MIRROR=1; shift ;;   # delete card files no longer in the library
        --list)           list_removable ;;
        -h|--help)        usage 0 ;;
        --) shift; [ -z "$DEST_PATH" ] && [ $# -gt 0 ] && { DEST_PATH="$1"; shift; }; break ;;
        -*) die "unknown option: $1" ;;
        *)  [ -z "$DEST_PATH" ] || die "unexpected arg: $1"; DEST_PATH="$1"; shift ;;
    esac
done

# --- Refuse to run as root ---------------------------------------------------
# Running the whole script under sudo makes rsync write root-owned files onto
# the card. EmuDeck/ES-DE and the emulators run as your normal user and then
# can't read or manage them — files show a red X and games fail to launch. The
# script elevates internally (sudo) only for the NAS mount, so start it as you.
if [ "$(id -u)" -eq 0 ]; then
    die "refusing to run as root — this would write root-owned ROMs the emulators can't read.
       Run it as your normal user; it prompts for sudo only when it needs to mount the NAS.
       (Already have root-owned ROMs from a past sudo run?  sudo chown -R you:you <card>/Emulation/roms/)"
fi

# --- Resolve the destination (card) ------------------------------------------
EXPLICIT_DEST=0
if [ -n "$DEST_PATH" ]; then
    EXPLICIT_DEST=1
else
    log "Looking for a card labeled '$SDCARD_LABEL'..."
    DEST_PATH="$(label_mount "$SDCARD_LABEL")"
    if [ -z "$DEST_PATH" ]; then
        # Labeled device present but not mounted? Auto-mount via udisks (no sudo).
        dev="$(label_dev "$SDCARD_LABEL")"
        [ -n "$dev" ] || die "no mounted or attached device with label '$SDCARD_LABEL' (try --list)"
        command -v udisksctl >/dev/null || die "$dev is not mounted and udisksctl is unavailable; mount it and pass -d"
        log "Found $dev (label $SDCARD_LABEL) unmounted; mounting..."
        udisksctl mount -b "$dev" >/dev/null || die "failed to mount $dev"
        DID_AUTOMOUNT=1
        DEST_PATH="$(label_mount "$SDCARD_LABEL")"
        [ -n "$DEST_PATH" ] || die "mounted $dev but could not locate its mountpoint"
    fi
fi

# Safety: never write unless the target sits on a real mount (a missing card must
# not silently fill the node's root disk). For the label path DEST_PATH is the
# mount root; for an explicit -d we only require it to live under *some* mount.
if [ "$EXPLICIT_DEST" -eq 1 ]; then
    findmnt -rno TARGET --target "$DEST_PATH" >/dev/null 2>&1 \
        || die "refusing to write: '$DEST_PATH' is not on a mounted filesystem"
    mp="$(findmnt -rno TARGET --target "$DEST_PATH")"
    [ "$mp" != "/" ] || die "refusing to write to a path on the root filesystem ('$DEST_PATH')"
else
    mountpoint -q "$DEST_PATH" || die "refusing to write: '$DEST_PATH' is not a mountpoint"
    [ "$DEST_PATH" != "/" ] || die "refusing to write to /"
fi

DEST="$DEST_PATH${DEST_SUBDIR:+/$DEST_SUBDIR}"

# --- Resolve the source (roms library) ---------------------------------------
CLEANUP_MNT=""
CREDS_FILE=""
cleanup() {
    [ -n "$CLEANUP_MNT" ] && { sudo umount "$CLEANUP_MNT" 2>/dev/null || true; rmdir "$CLEANUP_MNT" 2>/dev/null || true; }
    [ -n "$CREDS_FILE" ] && rm -f "$CREDS_FILE"
    return 0
}
trap cleanup EXIT

if [ -z "$GAMES_ROMS_SRC" ]; then
    # Mount the //NAS/games share read-only and use its roms/ subdir.
    [ -f "$ENV_FILE" ] || die "no GAMES_ROMS_SRC set and $ENV_FILE not found to mount the share"
    NAS_SERVER="$(env_get NAS_SERVER)";   [ -n "$NAS_SERVER" ]   || die "NAS_SERVER not set in $ENV_FILE"
    SMB_USERNAME="$(env_get SMB_USERNAME)"; [ -n "$SMB_USERNAME" ] || die "SMB_USERNAME not set in $ENV_FILE"
    SMB_PASSWORD="$(env_get SMB_PASSWORD)"; [ -n "$SMB_PASSWORD" ] || die "SMB_PASSWORD not set in $ENV_FILE"
    SMB_DOMAIN="$(env_get SMB_DOMAIN)"

    # Pass credentials via a 0600 file, never on the mount argv (which shows in ps).
    CREDS_FILE="$(mktemp)"; chmod 600 "$CREDS_FILE"
    { printf 'username=%s\n' "$SMB_USERNAME"
      printf 'password=%s\n' "$SMB_PASSWORD"
      [ -n "$SMB_DOMAIN" ] && printf 'domain=%s\n' "$SMB_DOMAIN"; } > "$CREDS_FILE"

    CLEANUP_MNT="$(mktemp -d /tmp/gamarr-games.XXXXXX)"
    log "Mounting //$NAS_SERVER/games (read-only)..."
    sudo mount -t cifs "//$NAS_SERVER/games" "$CLEANUP_MNT" \
        -o "credentials=$CREDS_FILE,vers=3.0,ro,soft,uid=$(id -u),gid=$(id -g)" \
        || die "failed to mount //$NAS_SERVER/games (need cifs-utils + sudo)"
    GAMES_ROMS_SRC="$CLEANUP_MNT/roms"
fi
[ -d "$GAMES_ROMS_SRC" ] || die "roms source '$GAMES_ROMS_SRC' does not exist"

# --- Copy --------------------------------------------------------------------
# FAT/exFAT can't store unix perms/owners/symlinks and has 2s mtime resolution,
# so drop perms/owner/group and widen the timestamp window. -r -t -D keeps it
# additive and resumable; timestamps let repeat runs skip unchanged files.
# Exclude gamarr's per-ROM tracking sidecars — they're clutter on the card and
# emulator frontends ignore them anyway.
RSYNC_OPTS=(-rtD --no-perms --no-owner --no-group --modify-window=2 --info=progress2 --human-readable --exclude='*.gamarr.json')
if [ "$DRY_RUN" -eq 1 ]; then
    RSYNC_OPTS+=(--dry-run)
    log "(dry run — no files will be written)"
else
    mkdir -p "$DEST"
fi
if [ "$MIRROR" -eq 1 ]; then
    RSYNC_OPTS+=(--delete)
    log "(mirror — card files missing from the library will be DELETED)"
fi

log "Source: $GAMES_ROMS_SRC/"
log "Dest:   $DEST/"
rsync "${RSYNC_OPTS[@]}" "$GAMES_ROMS_SRC/" "$DEST/"

if [ "$DRY_RUN" -eq 0 ]; then
    sync
    if [ "$DID_AUTOMOUNT" -eq 1 ] && command -v udisksctl >/dev/null; then
        log "Unmounting the card we auto-mounted..."
        udisksctl unmount -b "$(label_dev "$SDCARD_LABEL")" >/dev/null 2>&1 || true
        log "Done. Card unmounted — safe to remove."
    else
        log "Done. Safe to unmount and remove the card."
    fi
fi
