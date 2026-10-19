import type { components, operations } from './api-schema';

/** The API's own types, generated from its OpenAPI schema by scripts/generate-api-client.sh. */
type Schemas = components['schemas'];

export type Condition = Schemas['ConditionRule']['condition'];
/** Who submitted a price: a person, or a collector. Where it was seen is the offer's store. */
export type Provenance = Schemas['Observation']['provenance'];
export type Observation = Schemas['Observation'];
export type ConditionRule = Schemas['ConditionRule'];
/** A store offers are recorded under, as the listing filters and Add price offer it: a source's key and name.
 * 'other' names a one-off store by seller. */
export type Store = Pick<Source, 'key' | 'name'>;
export type PriceInput = Schemas['PriceInput'];
/** The price itself, apart from the offer it is of. */
export type ObservationInput = Pick<PriceInput, 'item_price_cents' | 'shipping_cents' | 'in_stock' | 'observed_at' | 'notes'>;
export type OfferEdit = Schemas['OfferEdit'];
export type Drive = Schemas['Drive'];
export type DriveEdit = Schemas['DriveEdit'];
export type OfferSummary = Schemas['OfferSummary'];
export type Offer = Schemas['Offer'];
export type ReviewItem = Schemas['ReviewItem'];
export type ReviewReason = ReviewItem['reason'];
export type Run = Schemas['Run'];
export type RunStatus = Run['status'];
export type CollectorStatus = Schemas['CollectorStatus'];
export type ListingFacts = Schemas['ListingFacts'];
export type SettingDescription = Schemas['SettingView'];
export type SourceKindDescription = Schemas['SourceKindView'];
/** The kind of a store: one the collector reads, or 'manual', entered by hand. */
export type SourceKind = SourceKindDescription['kind'];
/** A store as it is entered, and as the API shows it: the fields of its kind, chosen by kind. */
export type SourceInput = Schemas['ManualSourceInput'] | Schemas['ShopifySourceInput']
  | Schemas['SitemapSourceInput'] | Schemas['SapCommerceSourceInput'];
export type Source = Schemas['ManualSourceView'] | Schemas['ShopifySourceView']
  | Schemas['SitemapSourceView'] | Schemas['SapCommerceSourceView'];
export type SourceSettings = Source['settings'];
export type SourceBasis = Source['basis'];
export type SourceTransport = Source['transport'];
export type SourcePreviewInput = Schemas['ManualSourcePreviewInput'] | Schemas['ShopifySourcePreviewInput']
  | Schemas['SitemapSourcePreviewInput'] | Schemas['SapCommerceSourcePreviewInput'];
export type SourcePreview = Schemas['SourcePreview'];
export type InspectionCandidate = Schemas['ShopifyCandidate'] | Schemas['SitemapCandidate'] | Schemas['SapCommerceCandidate'];
export type SourceInspection = Schemas['SourceInspection'];
export type ReviewDecision = Schemas['MatchDecision'] | Schemas['IgnoreDecision'];
export type DecisionResult = Schemas['DecisionResult'];
/** Part of a long list, as the API serves it: these items, and how many there are in all. */
export type Page<T> = { items: T[]; total: number };
/** Which part of a list to serve: this many items, after skipping that many. */
export type PageRequest = { limit: number; offset: number };
/** Which offers waiting for review to read: those seen at one store, or waiting for one reason. */
export type ReviewFilter = { store?: string; reason?: ReviewReason };

export type TrendPoint = Schemas['TrendPoint'];
export type TrendSeries = Schemas['TrendSeries'];
export type Trends = Schemas['Trends'];
export type TrendSplit = NonNullable<Trends['by']>;
/** Which drives a report is of, narrowed as the drives list narrows them; empty for every drive. */
export type DriveScope = Omit<NonNullable<operations['price_trends']['parameters']['query']>, 'days' | 'by' | 'recent_days'>;

/** A price just recorded, named so that it can be taken back. */
export type RecordedPrice = { priceId: string };
export type PriceResult = Schemas['PriceResult'];

/** Which drives to list, as the server takes it: filters apply to offers, and a drive is listed when
 * any offer of it matches. Left out, a filter does not narrow. */
export type DriveQuery = NonNullable<operations['list_drives']['parameters']['query']>;
export type PriceRange = Schemas['PriceRange'];
export type DriveRow = Schemas['DriveRow'];
export type FilterOptions = Schemas['FilterOptions'];
export type DrivePage = Schemas['DrivePage'];
export type DriveDetail = Schemas['DriveDetail'];
/** Which of every drive to manage: by any name an offer of it goes by, and by what it needs. */
export type CatalogDriveQuery = NonNullable<operations['list_catalog_drives']['parameters']['query']>;
export type CatalogDrive = Schemas['CatalogDrive'];
export type CatalogDrivePage = Schemas['CatalogDrivePage'];
export type DriveIssue = Schemas['CatalogDrive']['issues'][number];
export type PriceRow = Schemas['PriceRow'];
export type PricePage = Schemas['PricePage'];
/** Prices of one drive's offers or of one offer, in effect at any time since since. */
export type PriceRequest = ({ driveId: string; offerId?: never } | { offerId: string; driveId?: never })
  & { since?: string; limit?: number; offset?: number };
export type PriceMark = Schemas['PriceMark'];
export type StoreFreshness = Schemas['StoreFreshness'];

export interface DisktrackerApi {
  /** A page of the drives that match, with what is said of every match and the filter options of every drive. */
  drives(query: DriveQuery): Promise<DrivePage>;
  /** A page of every drive to manage, held offers and all, with what each needs and how many of every drive need each thing. */
  catalogDrives(query: CatalogDriveQuery): Promise<CatalogDrivePage>;
  /** A drive with every offer of it, in every condition, with its ranges over rangeDays. */
  drive(id: string, rangeDays: number, recentDays: number): Promise<DriveDetail>;
  /** One offer with every price it has had. */
  offer(id: string): Promise<Offer>;
  /** A part of the prices of a drive's offers or of one offer, oldest first. */
  prices(request: PriceRequest): Promise<PricePage>;
  /** Offers entered by hand and not checked within the recent days, longest unchecked first. */
  offersToRecheck(recentDays: number): Promise<OfferSummary[]>;
  /** What each drive costs today in each condition it is in stock in, by the terabyte, cheapest first. */
  pricesToday(recentDays: number, scope: DriveScope): Promise<PriceMark[]>;
  /** Item prices across every drive over the days up to now, split when a split is asked for. */
  trends(days: number, by: TrendSplit | null, recentDays: number, scope: DriveScope): Promise<Trends>;
  /** How fresh each store's prices are: its offers, and when the latest and the middle were checked. */
  storeFreshness(): Promise<StoreFreshness[]>;
  /** The review queue, newest first, a page at a time. */
  reviewItems(query: PageRequest & ReviewFilter): Promise<Page<ReviewItem>>;
  decide(id: string, decision: ReviewDecision): Promise<DecisionResult>;
  /** Records a price for the offer described, creating the offer and its drive when they are new. */
  recordPrice(input: PriceInput, requestId: string): Promise<PriceResult>;
  /** Deletes a price, and its offer with it when it was the last; a price already gone is no error. */
  deletePrice(priceId: string): Promise<null>;
  editOffer(id: string, input: OfferEdit): Promise<Offer>;
  deleteOffer(id: string): Promise<void>;
  editDrive(driveId: string, input: DriveEdit): Promise<Drive>;
  addAlias(driveId: string, mpn: string): Promise<Drive>;
  /** The latest run of each store, by store. */
  latestRuns(): Promise<Run[]>;
  /** Every run that ended since a moment, oldest first. */
  recentRuns(since: string): Promise<Run[]>;
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

/** A query as parameters, a choice of several repeated; one left out or blank is not sent. */
function searchOf(query: object): URLSearchParams {
  const params = new URLSearchParams();
  for (const [name, value] of Object.entries(query)) {
    for (const one of Array.isArray(value) ? value : [value]) {
      if (one !== undefined && one !== null && one !== '') params.append(name, String(one));
    }
  }
  return params;
}

/** Query parameters with a scope's filters, a choice of several repeated. */
function scoped(fixed: Record<string, string | number>, scope: DriveScope): URLSearchParams {
  const params = new URLSearchParams(Object.entries(fixed).map(([name, value]) => [name, String(value)]));
  for (const [name, value] of Object.entries(scope)) {
    for (const one of Array.isArray(value) ? value : [value]) if (one !== undefined && one !== null && one !== '') params.append(name, String(one));
  }
  return params;
}

export class HttpDisktrackerApi implements DisktrackerApi {
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
  private async page<T>(path: string, { limit, offset, ...narrowed }: PageRequest & Record<string, string | number | undefined>): Promise<Page<T>> {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    for (const [name, value] of Object.entries(narrowed)) if (value !== undefined) params.set(name, String(value));
    const response = await this.request(`${this.baseUrl}${path}?${params}`, { method: 'GET', headers: {} });
    if (!response.ok) throw new Error(`Unable to save or load listings (${response.status}).`);
    const items = await response.json() as T[];
    return { items, total: Number(response.headers.get('X-Total-Count') ?? items.length) };
  }
  trends(days: number, by: TrendSplit | null, recentDays: number, scope: DriveScope): Promise<Trends> {
    return this.send(`/trends?${scoped({ days, recent_days: recentDays, ...(by ? { by } : {}) }, scope)}`);
  }
  reviewItems(query: PageRequest & ReviewFilter): Promise<Page<ReviewItem>> { return this.page('/review-items', query); }
  decide(id: string, decision: ReviewDecision): Promise<DecisionResult> {
    return this.send(`/review-items/${id}/decision`, decision, undefined, 'PUT');
  }
  addAlias(driveId: string, mpn: string): Promise<Drive> {
    return this.send(`/drives/${driveId}/aliases`, { mpn });
  }
  editDrive(driveId: string, input: DriveEdit): Promise<Drive> {
    return this.send(`/drives/${driveId}`, input, undefined, 'PATCH');
  }
  deleteOffer(id: string): Promise<void> {
    return this.send(`/offers/${id}`, undefined, undefined, 'DELETE');
  }
  storeFreshness(): Promise<StoreFreshness[]> { return this.send('/reports/store-freshness'); }
  drives(query: DriveQuery): Promise<DrivePage> { return this.send(`/drives?${searchOf(query)}`); }
  catalogDrives(query: CatalogDriveQuery): Promise<CatalogDrivePage> { return this.send(`/catalog-drives?${searchOf(query)}`); }
  drive(id: string, rangeDays: number, recentDays: number): Promise<DriveDetail> {
    return this.send(`/drives/${id}?range_days=${rangeDays}&recent_days=${recentDays}`);
  }
  offer(id: string): Promise<Offer> { return this.send(`/offers/${id}`); }
  prices({ driveId, offerId, since, limit = 500, offset = 0 }: PriceRequest): Promise<PricePage> {
    const params = new URLSearchParams(driveId ? { drive_id: driveId } : { offer_id: offerId! });
    if (since) params.set('since', since);
    params.set('limit', String(limit)); params.set('offset', String(offset));
    return this.send(`/prices?${params}`);
  }
  offersToRecheck(recentDays: number): Promise<OfferSummary[]> {
    return this.send(`/offers?needs_recheck=true&recent_days=${recentDays}`);
  }
  pricesToday(recentDays: number, scope: DriveScope): Promise<PriceMark[]> { return this.send(`/reports/prices-today?${scoped({ recent_days: recentDays }, scope)}`); }
  latestRuns(): Promise<Run[]> { return this.send('/collection-runs?latest_per_source=true'); }
  recentRuns(since: string): Promise<Run[]> { return this.send(`/collection-runs?${new URLSearchParams({ finished_since: since })}`); }
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
  recordPrice(input: PriceInput, requestId: string): Promise<PriceResult> {
    return this.send('/prices', input, requestId);
  }
  editOffer(id: string, input: OfferEdit): Promise<Offer> {
    return this.send(`/offers/${id}`, input, undefined, 'PATCH');
  }
  deletePrice(priceId: string): Promise<null> {
    return this.send(`/prices/${priceId}`, undefined, undefined, 'DELETE');
  }
}
