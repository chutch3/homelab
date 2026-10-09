import { useEffect, useState } from 'react';
import { specLabels, specLabel, specOptions, type SpecKey } from './specifications';
import { Button, Checkbox, MultiSelect, NativeSelect, TextInput, type ComboboxItem, type ComboboxLikeRenderOptionInput } from '@mantine/core';
import { capacityLabel, conditions } from './listing-display';
import type { Store } from './api';
import { brandLabel, defaultQuery, queryErrors, type BrandCount, type CapacityCount, type ConditionCount, type ListingQuery } from './listing-query';

/** capacities and brands are those of the drives loaded, each with how many drives have it. */
/** An option shows how many drives have it; the chosen chip shows only its name. */
const withCount = (drives: Map<string, number>) => ({ option, checked }: ComboboxLikeRenderOptionInput<ComboboxItem>) =>
  <span className="count-option"><span className="option-check" aria-hidden="true">{checked ? '✓' : ''}</span>
    {option.label} <span className="option-count">({drives.get(option.value)})</span></span>;
/** How long typing a total must pause before it is applied. */
const TYPING_PAUSE_MS = 400;
/** The specifications kept under More filters; the media type is on the first row. */
const moreSpecs = (Object.keys(specLabels) as SpecKey[]).filter(key => key !== 'media_type');

type Props = {
  query: ListingQuery; onChange: (query: ListingQuery) => void; recentDays: number; stores: Store[];
  capacities: CapacityCount[]; brands: BrandCount[];
  /** The conditions the drives loaded are sold in, each with how many drives are. */
  conditions: ConditionCount[];
};
/** The filters used most on one row, the conditions to accept as buttons under it, the rest under
 * More filters, and a chip for each other filter in force. */
export function ListingFilters({ query, onChange, recentDays, stores, capacities, brands, conditions: sold }: Props) {
  const errors = queryErrors(query);
  const update = (change: Partial<ListingQuery>) => onChange({ ...query, ...change });
  // A total is applied once typing pauses, so a half-typed amount never filters the list.
  const [maxTotal, setMaxTotal] = useState(query.maxTotal);
  useEffect(() => setMaxTotal(query.maxTotal), [query.maxTotal]);
  const applyMaxTotal = () => { if (maxTotal !== query.maxTotal) update({ maxTotal }); };
  useEffect(() => {
    if (maxTotal === query.maxTotal) return;
    const pause = setTimeout(applyMaxTotal, TYPING_PAUSE_MS);
    return () => clearTimeout(pause);
  });
  const [more, setMore] = useState(false);
  const specSelect = (key: SpecKey) => <NativeSelect key={key} label={specLabels[key]} aria-label={specLabels[key]}
    data={[{ value: '', label: 'Any' }, ...specOptions[key].filter(option => option.value !== 'unknown'), { value: 'unknown', label: 'Unknown' }]} value={query[key]}
    onChange={event => update({ [key]: event.currentTarget.value })} />;
  const without = (values: string[], value: string) => values.filter(other => other !== value);
  const storeName = (key: string) => stores.find(store => store.key === key)?.name ?? key;
  /** Every filter in force, with the change that takes it off again; those under More filters are marked. */
  const active: { label: string; remove: Partial<ListingQuery>; more?: boolean }[] = [
    ...(query.search ? [{ label: `Search: ${query.search}`, remove: { search: '' } }] : []),
    ...(query.media_type ? [{ label: `${specLabels.media_type}: ${specLabel('media_type', query.media_type)}`, remove: { media_type: '' } }] : []),
    ...query.capacities.map(value => ({ label: capacityLabel(Number(value)), remove: { capacities: without(query.capacities, value) } })),
    ...(query.maxTotal ? [{ label: `Total up to $${query.maxTotal}`, remove: { maxTotal: '' } }] : []),
    ...query.brands.map(value => ({ label: brandLabel(value), remove: { brands: without(query.brands, value) }, more: true })),
    ...query.stores.map(value => ({ label: storeName(value), remove: { stores: without(query.stores, value) }, more: true })),
    ...moreSpecs.filter(key => query[key]).map(key => ({ label: `${specLabels[key]}: ${specLabel(key, query[key])}`, remove: { [key]: '' }, more: true })),
    ...(query.inStockOnly ? [{ label: 'In stock only', remove: { inStockOnly: false }, more: true }] : []),
    ...(query.recentOnly ? [{ label: `Checked within ${recentDays} days`, remove: { recentOnly: false }, more: true }] : []),
  ];
  const hidden = active.filter(filter => filter.more).length;
  return <section className="listing-filters" aria-label="Filter drives">
    <div className="filter-grid">
      <TextInput label="Search drives" aria-label="Search drives" placeholder="Name, MPN or store" value={query.search} onChange={event => update({ search: event.currentTarget.value })} />
      {specSelect('media_type')}
      <MultiSelect label="Capacity" placeholder={query.capacities.length ? undefined : 'Any'} searchable clearable
        data={capacities.map(({ capacity_gb }) => ({ value: String(capacity_gb), label: capacityLabel(capacity_gb) }))}
        renderOption={withCount(new Map(capacities.map(({ capacity_gb, drives }) => [String(capacity_gb), drives])))}
        value={query.capacities} onChange={values => update({ capacities: values })} />
      <TextInput label="Maximum total (USD)" aria-label="Maximum total (USD)" inputMode="decimal" value={maxTotal} error={errors.maxTotal}
        placeholder="No limit" onChange={event => setMaxTotal(event.currentTarget.value)}
        onBlur={applyMaxTotal} onKeyDown={event => { if (event.key === 'Enter') applyMaxTotal(); }} />
    </div>
    {/* Which conditions to accept: none chosen is any. Each drive is priced and ordered by its offers in them. */}
    <div role="group" aria-label="Condition" className="condition-filter">
      <span className="condition-filter-label">Condition</span>
      {conditions.filter(({ value }) => sold.some(count => count.condition === value) || query.conditions.includes(value)).map(({ value, label }) => {
        const pressed = query.conditions.includes(value);
        return <button key={value} type="button" className="chip toggle" aria-pressed={pressed}
          onClick={() => update({ conditions: pressed ? without(query.conditions, value) : conditions.map(option => option.value).filter(option => option === value || query.conditions.includes(option)) })}>
          {label} ({sold.find(count => count.condition === value)?.drives ?? 0})</button>;
      })}
    </div>
    <div className="filter-tools">
      <Button variant="default" aria-expanded={more} onClick={() => setMore(!more)}
        rightSection={<span aria-hidden="true">{more ? '−' : '+'}</span>}>{hidden ? `More filters (${hidden})` : 'More filters'}</Button>
      {active.length > 0 && <ul className="chips" aria-label="Active filters">{active.map(({ label, remove }) => <li key={label}>
        <button type="button" className="chip" aria-label={`Remove filter: ${label}`} onClick={() => update(remove)}>{label}<span aria-hidden="true"> ×</span></button></li>)}</ul>}
      {(active.length > 0 || query.conditions.length > 0) && <Button variant="subtle" onClick={() => onChange({ ...defaultQuery(), sort: query.sort })}>Clear filters</Button>}
    </div>
    {more && <div className="more-filter-grid">
      <MultiSelect label="Brand" placeholder={query.brands.length ? undefined : 'Any'} searchable clearable
        data={brands.map(({ brand }) => ({ value: brand, label: brandLabel(brand) }))}
        renderOption={withCount(new Map(brands.map(({ brand, drives }) => [brand, drives])))}
        value={query.brands} onChange={values => update({ brands: values })} />
      <MultiSelect label="Store" placeholder={query.stores.length ? undefined : 'Any'} clearable
        data={stores.map(store => ({ value: store.key, label: store.name }))} value={query.stores} onChange={values => update({ stores: values })} />
      {moreSpecs.map(specSelect)}
      <Checkbox label="In stock only" checked={query.inStockOnly} onChange={event => update({ inStockOnly: event.currentTarget.checked })} />
      <Checkbox label={`Checked in the last ${recentDays} days`} checked={query.recentOnly} onChange={event => update({ recentOnly: event.currentTarget.checked })} />
    </div>}
  </section>;
}
