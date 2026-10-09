import type { Specifications } from './specifications';
export type ObservationInput = {
  item_price_cents: number | null; shipping_cents: number; in_stock: boolean; observed_at: string | null; notes: string;
};
export type Observation = {
  id: string; item_price_cents: number; shipping_cents: number | null; shipping_known: boolean; in_stock: boolean;
  observed_at: string; entered_at: string;
  /** 'manual' when a person entered it, otherwise the collector source that recorded it. */
  notes: string; acquisition_method: string; total_cents: number; price_per_tb: string;
};
export type Condition = 'new' | 'manufacturer_recertified' | 'refurbished' | 'used';
/** Text matching the pattern (a case-insensitive regular expression) names the condition. */
export type ConditionRule = { pattern: string; condition: Condition };
/** A store offers are recorded under, as the listing filters and Add price offer it: a source's key and name.
 * 'other' names a one-off store by seller. */
export type Store = Pick<Source, 'key' | 'name'>;
export type PriceInput = ObservationInput & {
  mpn: string; store: string; seller: string; condition: Condition; title: string | null; url: string | null; capacity_gb: number | null;
};
export type OfferEdit = { title: string; url: string | null };
/** brand is the drive's maker (Seagate, Western Digital…), or null until a source names it. */
export type Drive = { id: string; mpn: string; aliases: string[]; brand: string | null; capacity_gb: number; specifications: Specifications };
/** brand: the drive's maker as corrected by hand; blank makes it unknown again, for a source to name. */
export type DriveInput = { capacity_gb: number; specifications: Specifications; brand: string };
/** An offer with its latest price, as the listings table shows it. */
export type ListingSummary = {
  id: string; title: string; mpn: string | null; store: string; store_name: string; seller: string; url: string | null;
  capacity_gb: number; condition: Condition; drive: Drive | null; last_checked_at: string;
  latest: Observation;
};
/** An offer with every price it has had, oldest first. */
export type Listing = ListingSummary & { observations: Observation[] };
export type UnmatchedReason = 'missing_mpn' | 'missing_condition' | 'capacity_conflict' | 'missing_capacity' | 'missing_price';
export type UnmatchedItem = {
  /** source: the key of the source it was read from, which is its store. */
  id: string; source: string; url: string; title: string; seller: string;
  mpn: string | null; condition: Condition | null; capacity_gb: number | null;
  item_price_cents: number | null; shipping_cents: number | null; in_stock: boolean;
  reason: UnmatchedReason; first_seen_at: string; last_seen_at: string;
};
/** How one collector run went, as the collector reported it. */
export type CollectorRun = {
  source: string; started_at: string; finished_at: string; completed: boolean;
  seen: number; recorded: number; queued: number; ignored: number; failed: number; rechecked: number; recheck_failed: number;
  /** It ended early because it was asked to stop, rather than failing. */
  stopped: boolean;
};
/** A run in progress: how far the collector last said it had got, and when it said so. */
export type RunProgress = {
  source: string; started_at: string; updated_at: string;
  seen: number; recorded: number; queued: number; ignored: number; failed: number;
};
/** What the collector is doing: when it was last heard from (never: null), the runs in progress,
 * and the keys of the sources waiting to run, in the order they will. */
export type CollectorStatus = { seen_at: string | null; running: RunProgress[]; waiting: string[] };
/** What pasted listing text says of an offer; anything it does not say is null. */
export type ListingFacts = {
  title: string | null; mpn: string | null; capacity_gb: number | null; condition: Condition | null;
  brand: string | null; item_price_cents: number | null;
};
/** manual: a store whose offers are entered by hand, never collected. */
/** The kind of a store: one the collector reads, or 'manual', entered by hand. The kinds there are, and
 * what each needs to know, come from the API (listSourceKinds). */
export type SourceKind = string;
/** One thing a kind of store needs to know, as its reader describes it. */
export type SettingDescription = {
  name: string; label: string; type: 'text' | 'list' | 'flag'; required: boolean; description: string; placeholder: string;
  /** The group of settings it is asked for among; '' for none. */
  group: string; pattern: string; pattern_message: string; regex: boolean; capturing: boolean; needs: string;
};
/** A kind of store: what it is called, whether it is collected, whether one of its pages can be read
 * alone to test it, and its settings, some of them in groups. */
export type SourceKindDescription = {
  kind: SourceKind; label: string; collected: boolean; page_test: boolean;
  groups: { name: string; label: string; help: string }[]; settings: SettingDescription[];
};
/** What allows collecting from a source; recorded so the decision is visible, not enforced. */
export type SourceBasis = 'permission' | 'terms_allow' | 'open_api' | 'unconfirmed';
export type SourceTransport = 'direct' | 'browser';
/** A store offers are recorded under: read by a collector on a cron schedule, with settings for its kind, or entered by hand. */
export type SourceInput = {
  name: string; kind: SourceKind; base_url: string; settings: SourceSettings; schedule: string;
  enabled: boolean; transport: SourceTransport; basis: SourceBasis; notes: string;
};
export type SourceSettings = Record<string, string | boolean | string[]>;
/** key is what its prices and runs are recorded under, fixed when it is created. */
/** next_run_at is when the source is next due (in the past while it waits for the collector); null while switched off. */
/** One offer as the collector read it from a source being tested, and what disktracker would do with it.
 * status: found, nothing (the store was read but no drive found), or failed (for the reason given). */
export type SourcePreview = {
  status: 'found' | 'nothing' | 'failed'; reason: string | null;
  offer: {
    url: string; title: string; mpn: string | null; brand: string | null; condition: Condition | null; capacity_gb: number | null;
    item_price_cents: number | null; shipping_cents: number | null; in_stock: boolean; aliases: string[];
  } | null;
  verdict: { outcome: 'recorded' | 'review' | 'ignored'; reason: string | null } | null;
  /** What the collector read on the way, and why a page gave no offer. */
  notes: string[];
};
/** A source to try. page_url: one of its pages to read instead of those its sitemap lists. */
export type SourcePreviewInput = SourceInput & { page_url?: string };
/** One way of reading the store a link is from: the kind of source and its settings, why they were
 * chosen, how many offers they read from the page, the first of them, and what would become of it. */
export type InspectionCandidate = {
  kind: SourceKind; settings: SourceSettings; evidence: string[]; offers: number;
  /** How much there is to the store read this way, and how long a run of it would take. */
  summary: { label: string; value: string }[];
  offer: NonNullable<SourcePreview['offer']>; verdict: NonNullable<SourcePreview['verdict']>;
};
/** What inspecting a link to one product page found: the ways of reading its store, best first. */
export type SourceInspection = {
  status: 'found' | 'nothing' | 'failed'; reason: string | null; base_url: string;
  candidates: InspectionCandidate[]; notes: string[];
};
export type Source = SourceInput & { id: string; key: string; next_run_at: string | null };
export type Resolution = { mpn: string; condition: Condition; capacity_gb: number | null };
/** Part of a long list, as the API serves it: these items, and how many there are in all. */
export type Page<T> = { items: T[]; total: number };
/** Which part of a list to serve: this many items, after skipping that many. */
export type PageRequest = { limit: number; offset: number };

export interface ListingsApi {
  /** The review queue, newest first, a page at a time. */
  listUnmatched(page: PageRequest): Promise<Page<UnmatchedItem>>;
  resolveUnmatched(id: string, resolution: Resolution): Promise<Listing>;
  ignoreUnmatched(id: string): Promise<void>;
  recordPrice(input: PriceInput, requestId: string): Promise<Listing>;
  deletePrice(id: string, observationId: string): Promise<Listing | null>;
  editOffer(id: string, input: OfferEdit): Promise<Listing>;
  deleteOffer(id: string): Promise<void>;
  replaceSpecifications(driveId: string, input: DriveInput): Promise<Drive>;
  addAlias(driveId: string, mpn: string): Promise<Drive>;
  list(): Promise<ListingSummary[]>;
  priceHistory(ids: string[]): Promise<Listing[]>;
  latestRuns(): Promise<CollectorRun[]>;
  readListing(text: string): Promise<ListingFacts>;
  listSources(): Promise<Source[]>;
  listSourceKinds(): Promise<SourceKindDescription[]>;
  addSource(input: SourceInput): Promise<Source>;
  updateSource(id: string, input: SourceInput): Promise<Source>;
  /** Makes the source due now, ahead of those only scheduled, whether it is switched on or not. */
  runSource(id: string): Promise<Source>;
  /** Asks the source's run in progress to stop; the collector learns of it within seconds. */
  stopSource(id: string): Promise<Source>;
  collectorStatus(): Promise<CollectorStatus>;
  /** Deletes a source nothing is recorded under; one with offers is refused. */
  deleteSource(id: string): Promise<void>;
  /** Reads one offer from a source, saved or not, without keeping anything. */
  previewSource(input: SourcePreviewInput): Promise<SourcePreview>;
  /** From a link to one product page of a store not read yet: how the store would be read. */
  inspectLink(url: string, transport: SourceTransport): Promise<SourceInspection>;
  listConditionRules(): Promise<ConditionRule[]>;
  /** Replaces every rule, in the order given. */
  replaceConditionRules(rules: ConditionRule[]): Promise<ConditionRule[]>;
}

export class ApiValidationError extends Error {
  constructor(readonly fields: Record<string, string>) {
    super('Check the submitted entry.');
    this.name = 'ApiValidationError';
  }
}

export function validationError(detail: unknown): ApiValidationError | null {
  if (!Array.isArray(detail)) return null;
  const fields: Record<string, string> = {};
  for (const issue of detail) {
    if (issue && Array.isArray(issue.loc) && issue.loc[0] === 'body' && typeof issue.msg === 'string') {
      fields[issue.loc.slice(1).join('.')] = issue.msg;
    }
  }
  return Object.keys(fields).length ? new ApiValidationError(fields) : null;
}

export class HttpListingsApi implements ListingsApi {
  constructor(private readonly request: typeof fetch, private readonly baseUrl: string) {}
  private async send<T>(path: string, body?: unknown, requestId?: string, method = body === undefined ? 'GET' : 'POST'): Promise<T> {
    const headers: Record<string, string> = body === undefined ? {} : { 'Content-Type': 'application/json' };
    if (requestId) headers['Idempotency-Key'] = requestId;
    const response = await this.request(`${this.baseUrl}${path}`, {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) {
      const problem = await response.json().catch(() => null);
      const detail = problem?.detail;
      const fieldError = response.status === 422 ? validationError(detail) : null;
      if (fieldError) throw fieldError;
      throw new Error(typeof detail === 'string' ? detail : `Unable to save or load listings (${response.status}).`);
    }
    return (response.status === 204 ? null : response.json()) as Promise<T>;
  }
  /** A page of a list the API serves in parts: X-Total-Count says how many there are in all. */
  private async page<T>(path: string, { limit, offset }: PageRequest): Promise<Page<T>> {
    const response = await this.request(`${this.baseUrl}${path}?limit=${limit}&offset=${offset}`, { method: 'GET', headers: {} });
    if (!response.ok) throw new Error(`Unable to save or load listings (${response.status}).`);
    const items = await response.json() as T[];
    return { items, total: Number(response.headers.get('X-Total-Count') ?? items.length) };
  }
  listUnmatched(page: PageRequest): Promise<Page<UnmatchedItem>> { return this.page('/unmatched', page); }
  resolveUnmatched(id: string, resolution: Resolution): Promise<Listing> {
    return this.send(`/unmatched/${id}/resolve`, resolution);
  }
  ignoreUnmatched(id: string): Promise<void> {
    return this.send(`/unmatched/${id}/ignore`, undefined, undefined, 'POST');
  }
  addAlias(driveId: string, mpn: string): Promise<Drive> {
    return this.send(`/drives/${driveId}/aliases`, { mpn });
  }
  replaceSpecifications(driveId: string, input: DriveInput): Promise<Drive> {
    return this.send(`/drives/${driveId}/specifications`, input, undefined, 'PUT');
  }
  deleteOffer(id: string): Promise<void> {
    return this.send(`/listings/${id}`, undefined, undefined, 'DELETE');
  }
  list(): Promise<ListingSummary[]> { return this.send('/listings'); }
  priceHistory(ids: string[]): Promise<Listing[]> {
    return this.send(`/price-history?${new URLSearchParams(ids.map(id => ['listing', id]))}`);
  }
  latestRuns(): Promise<CollectorRun[]> { return this.send('/collector-runs/latest'); }
  readListing(text: string): Promise<ListingFacts> { return this.send('/listing-text', { text }); }
  listSources(): Promise<Source[]> { return this.send('/sources'); }
  listSourceKinds(): Promise<SourceKindDescription[]> { return this.send('/source-kinds'); }
  addSource(input: SourceInput): Promise<Source> { return this.send('/sources', input); }
  updateSource(id: string, input: SourceInput): Promise<Source> { return this.send(`/sources/${id}`, input, undefined, 'PUT'); }
  runSource(id: string): Promise<Source> { return this.send(`/sources/${id}/run`, {}); }
  stopSource(id: string): Promise<Source> { return this.send(`/sources/${id}/stop`, {}); }
  collectorStatus(): Promise<CollectorStatus> { return this.send('/collector-status'); }
  deleteSource(id: string): Promise<void> { return this.send(`/sources/${id}`, undefined, undefined, 'DELETE'); }
  previewSource(input: SourcePreviewInput): Promise<SourcePreview> { return this.send('/source-previews', input); }
  inspectLink(url: string, transport: SourceTransport): Promise<SourceInspection> { return this.send('/source-inspections', { url, transport }); }
  listConditionRules(): Promise<ConditionRule[]> { return this.send('/condition-rules'); }
  replaceConditionRules(rules: ConditionRule[]): Promise<ConditionRule[]> { return this.send('/condition-rules', rules, undefined, 'PUT'); }
  recordPrice(input: PriceInput, requestId: string): Promise<Listing> {
    return this.send('/prices', input, requestId);
  }
  editOffer(id: string, input: OfferEdit): Promise<Listing> {
    return this.send(`/listings/${id}`, input, undefined, 'PATCH');
  }
  deletePrice(id: string, observationId: string): Promise<Listing | null> {
    return this.send(`/listings/${id}/observations/${observationId}`, undefined, undefined, 'DELETE');
  }
}
