import { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Button, Text } from '@mantine/core';
import type { DisktrackerApi, DriveScope, Source, Trends, TrendSeries, TrendSplit } from './api';
import { capacityLabel, conditionLabel, dollars } from './listing-display';
import { brandLabel, scopeOf, scopeSearch } from './listing-query';
import { specLabel, specLabels, type SpecKey } from './specifications';
import { movedLabel, summaryOf } from './trend-summary';
import { TrendChart } from './TrendChart';
import { pathFor, trendPeriods, type TrendPeriod, type TrendQuery } from './view';

/** The fewest drives a typical price is worth quoting for. */
const MIN_DRIVES = 3;
const DAY = 86_400_000;
/** A day as a month and its day, in UTC as the server counts days. */
const day = (moment: number) => new Date(moment).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
const splitNames: [TrendSplit | null, string][] = [[null, 'None'], ['condition', 'Condition'], ['capacity', 'Capacity'], ['store', 'Store']];
const headings: Record<TrendSplit, string> = { condition: 'By condition', capacity: 'By capacity', store: 'By store, against typical price' };
/** Hundredths of a percent, as a signed percentage. */
const percent = (value: number) => `${value > 0 ? '+' : value < 0 ? '−' : ''}${Math.abs(value / 100).toFixed(1)}%`;
/** A range that takes in every value, opened out to whole steps. */
function domainOf(values: number[], step: number): [number, number] {
  const low = Math.floor(Math.min(...values) / step) * step, high = Math.ceil(Math.max(...values) / step) * step;
  return high > low ? [low, high] : [low - step, high + step];
}

type Props = {
  api: DisktrackerApi;
  /** The path the app is served under, for the way from a part to its drives. */
  base: string; recentDays: number;
  /** The stores, to name each by. */
  stores: Source[];
  query: TrendQuery; onChange: (query: TrendQuery) => void;
  now: () => Date;
};

/** The filters a scope was narrowed by, in words: the search, then each choice as the app names it. */
function scopeWords({ scope }: TrendQuery, stores: Source[]): string {
  const specs = (Object.keys(specLabels) as SpecKey[]).filter(key => scope[key]).map(key => specLabel(key, scope[key]));
  return [
    ...(scope.search.trim() ? [`“${scope.search.trim()}”`] : []),
    ...scope.conditions.map(conditionLabel), ...scope.capacities.map(size => capacityLabel(Number(size))),
    ...scope.brands.map(brandLabel), ...scope.stores.map(key => stores.find(found => found.key === key)?.name ?? key), ...specs,
  ].join(', ');
}

/** How a trend has moved, with an arrow for the eye and the word for a screen reader, and what it is over. */
function Moved({ series, days, relative }: { series: TrendSeries; days: number; relative: boolean }) {
  const summary = summaryOf(series)!, { down, text } = movedLabel(summary.start, summary.today, Math.min(days, summary.since), relative);
  return <>{down !== null && <><span aria-hidden="true">{down ? '↓ ' : '↑ '}</span><span className="visually-hidden">{down ? 'Down ' : 'Up '}</span></>}{text}</>;
}

/** Item prices across every drive over a period: what a terabyte typically costs and how that has
 * moved, then the same for each condition, capacity or store when the market is split by one. */
export function TrendsView({ api, base, recentDays, stores, query, onChange, now }: Props) {
  const { by } = query;
  /** The period shown when none was chosen and the usual one has no trend: the longest prices go back over. */
  const [fallback, setFallback] = useState<TrendPeriod | null>(null);
  const days: TrendPeriod = query.days ?? fallback ?? 90;
  const narrowed = scopeSearch(query.scope);
  const scope = useMemo(() => JSON.stringify(scopeOf(query.scope)), [query.scope]);
  const [trends, setTrends] = useState<Trends | null>(null);
  const [error, setError] = useState('');
  const load = useCallback((active: () => boolean = () => true) => {
    setError('');
    return api.trends(days, by, recentDays, JSON.parse(scope) as DriveScope).then(found => {
      if (!active()) return;
      setTrends(found);
      // A period no drive is followed over, that nobody chose: the longest the prices cover instead.
      if (query.days !== null || summaryOf(found.market) || found.since === null) return;
      const covered = Math.floor((now().getTime() - Date.parse(found.since)) / DAY);
      const longest = [...trendPeriods].reverse().find(period => period <= covered);
      if (longest !== undefined && longest < days) setFallback(longest);
    }).catch(err => { if (active()) setError(err instanceof Error ? err.message : 'Unknown error.'); });
  }, [api, days, by, recentDays, scope, query.days, now]);
  useEffect(() => {
    let active = true;
    void load(() => active);
    return () => { active = false; };
  }, [load]);
  const market = trends && summaryOf(trends.market);
  // What is shown belongs to the split it was asked for: a new choice waits for its own answer.
  const parts = trends?.by === by ? trends.parts : [];
  const store = by === 'store';
  const nameOf = (key: string) => by === 'condition' ? conditionLabel(key) : by === 'capacity' ? capacityLabel(Number(key)) : stores.find(found => found.key === key)?.name ?? key;
  const show = store ? percent : dollars;
  // An axis counts in whole dollars where it can; the figures beside a chart keep their cents.
  const onAxis = (value: number) => store || value % 100 ? show(value) : `$${value / 100}`;
  const shown = parts.flatMap(({ series }) => series.points.flatMap(point => [point.low, point.median, point.high]));
  // Every part shares one scale, so heights compare across them.
  const shared = shown.length ? domainOf(store ? [...shown, 0] : shown, store ? 500 : 200) : [0, 1] as [number, number];
  return <>
    <h1>Trends</h1>
    {narrowed && <section aria-label="Drives followed" className="trend-scope">
      <Text size="sm">Drives matching {scopeWords(query, stores)}.</Text>
      <a className="seller-link" href={`${base}?${narrowed}`}>See these drives</a>
      <a className="seller-link" href={pathFor('trends', base)}>Every drive</a>
    </section>}
    {error && <Alert color="red" role="alert" mb="md" title="Trends could not be loaded">
      <Text size="sm" mb="sm">{error}</Text><Button variant="default" onClick={() => { void load(); }}>Try again</Button></Alert>}
    <section aria-labelledby="typical-heading" className="trend-market">
      <h2 id="typical-heading">Typical item price per TB</h2>
      {/* Unlike Prices, which ranks by what you pay: shipping would make a trend of what is not known. */}
      <Text size="sm" c="dimmed">Shipping is left out: many stores don’t say what it costs.</Text>
      {/* The period and the split sit in the chart they change: today's prices, below, have neither. */}
      <div className="trend-filters">
        <div role="group" aria-label="Period" className="trend-choice segmented">{trendPeriods.map(period =>
        <Button key={period} size="xs" variant={period === days ? 'filled' : 'default'} aria-pressed={period === days} onClick={() => onChange({ ...query, days: period })}>{period} days</Button>)}</div>
        <div role="group" aria-label="Split by" className="trend-choice segmented"><span className="trend-choice-label" aria-hidden="true">Split by</span>{splitNames.map(([split, name]) =>
        <Button key={name} size="xs" variant={split === by ? 'filled' : 'default'} aria-pressed={split === by} onClick={() => onChange({ ...query, by: split })}>{name}</Button>)}</div>
      </div>
      {trends && !market && <Text size="sm">{trends.since === null ? 'No prices have been recorded yet.'
        : `No drive has prices going back ${days} days yet: prices go back to ${day(Date.parse(trends.since))}, so a ${days}-day trend starts on ${day(Date.parse(trends.since) + days * DAY)}.`}</Text>}
      {trends && market && query.days === null && fallback !== null && trends.since !== null
        && <Text size="sm">Over the last {days} days, the longest there is: prices go back to {day(Date.parse(trends.since))}.</Text>}
      {trends && market && <>
        <p className="trend-figure"><span className="trend-label">Today</span><strong>{dollars(market.today)}</strong> <span>per TB</span></p>
        <p className="trend-moved"><Moved series={trends.market} days={days} relative /></p>
        <p className="trend-note">Middle half {dollars(market.low)} to {dollars(market.high)}</p>
        <TrendChart series={trends.market} days={days} band rule={market.average} format={onAxis}
          domain={domainOf(trends.market.points.flatMap(point => [point.low, point.high]), 200)} />
        <p className="trend-note">{trends.market.counted} of {trends.market.of} drives with a full {days} days of prices.</p>
      </>}
    </section>
    {by && parts.length > 0 && <>
      <h2>{headings[by]}</h2>
      {store && <Text size="sm" c="dimmed">Each store against the typical price for the same drives. Below zero is cheaper.</Text>}
      <div className="trend-parts">{parts.map(({ key, series }) => {
        const summary = summaryOf(series), thin = series.counted < MIN_DRIVES;
        return <section key={key} aria-label={nameOf(key)} className="trend-part">
          <h3>{nameOf(key)}</h3>
          {!summary ? <Text size="sm" c="dimmed">{store ? 'No shared drives to compare.' : `No ${days}-day history.`}</Text>
            // Too few drives to speak of a typical one: the chart is shown, and no figure is claimed for it.
            : thin ? <Text size="sm" c="dimmed">{series.counted} drive{series.counted === 1 ? '' : 's'}, too few</Text> : <>
              <p className="trend-figure"><strong>{show(summary.today)}</strong> <span>{store ? 'vs typical' : 'per TB'}</span></p>
              <p className="trend-moved"><Moved series={series} days={days} relative={!store} />, {series.counted} drives</p>
            </>}
          {summary && <div className={thin ? 'trend-thin' : undefined}><TrendChart series={series} days={days} domain={shared} band={!thin} rule={store ? 0 : undefined} format={onAxis} height={120} /></div>}
          <a className="seller-link" href={`${base}?${new URLSearchParams([...new URLSearchParams(narrowed), [by, key]])}`}>See drives</a>
        </section>;
      })}</div>
    </>}
  </>;
}
