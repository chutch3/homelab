import { useRef, useState, type CSSProperties, type KeyboardEvent } from 'react';
import type { Condition } from './api';
import { capacityLabel, conditionLabel, conditions, dollars } from './listing-display';
import { along, railBands, RAIL_BANDS, type Rail, type RailBand } from './rail-marks';

type Props = {
  /** Every drive in stock gathered into bands of price, or null when none is. */
  rail: Rail | null;
  /** Opens a drive (by its group key) on the condition of the mark chosen. */
  onSelect: (key: string, condition: Condition) => void;
};

/** Cents as a ruler names them: whole dollars without their cents, and cents alone under a dollar. */
const rulerLabel = (cents: number) => cents < 100 ? `${cents}¢` : `$${(cents / 100).toLocaleString('en-US')}`;

/** Today's prices as one picture: how many drives are in stock at each price per terabyte, cheaper
 * to the left, every condition counted together until one is chosen. Drives whose prices fall
 * together are one bar, as tall as there are drives in it, and opening it opens the cheapest; the few
 * far dearer than the rest are gathered past the ruler's end, under More. The cheapest is read out
 * until another bar is pointed at or focused; the bars are one stop for the Tab key, with the arrow
 * keys moving along them in order of price. */
export function DriveRail({ rail, onSelect }: Props) {
  const [chosen, setChosen] = useState<Condition | null>(null);
  const [pointed, setPointed] = useState<number | null>(null);
  const [stop, setStop] = useState<number | null>(null);
  const track = useRef<HTMLDivElement>(null);
  if (!rail) return <section aria-labelledby="rail-heading" className="rail"><h2 id="rail-heading">Prices today</h2><p>No drive is in stock.</p></section>;
  const sold = conditions.filter(({ value }) => rail.bands.some(band => band.condition === value));
  // A condition chosen can sell out as prices are reloaded: every condition is shown again.
  const condition = sold.some(({ value }) => value === chosen) ? chosen : null;
  const bands = railBands(rail, condition);
  const lowest = Math.max(0, bands.findIndex(band => band.lowest));
  const most = Math.max(...bands.map(band => band.drives));
  const count = (drives: number) => `${drives.toLocaleString('en-US')} drive${drives === 1 ? '' : 's'}`;
  const name = (band: RailBand) => `${band.cheapest.title} ${capacityLabel(band.cheapest.capacityGb)}`;
  const price = (band: RailBand) => dollars(band.cheapest.perTb);
  /** Where a band's drives are priced: one drive's own price, the band's ends, or past the ruler's. */
  const reach = (band: RailBand) => band.to === null ? `More than ${dollars(band.from)} per TB`
    : band.drives === 1 ? `${price(band)} per TB` : `${dollars(Math.round(band.from))} to ${dollars(Math.round(band.to))} per TB`;
  const label = (band: RailBand) => band.drives === 1 ? `${name(band)}, ${conditionLabel(band.cheapest.condition).toLowerCase()}, ${price(band)} per TB`
    : `${count(band.drives)}, ${reach(band).replace(/^More/, 'more')}, cheapest ${name(band)} at ${price(band)}`;
  const read = bands[pointed ?? lowest] ?? bands[lowest];
  const move = (event: KeyboardEvent, from: number) => {
    const to = { ArrowRight: from + 1, ArrowLeft: from - 1, Home: 0, End: bands.length - 1 }[event.key];
    if (to === undefined) return;
    event.preventDefault();
    if (!bands[to]) return;
    setStop(to);
    track.current?.querySelector<HTMLButtonElement>(`[data-index="${to}"]`)?.focus();
  };
  const choose = (next: Condition | null) => { setChosen(next); setPointed(null); setStop(null); };
  const beyond = bands.some(band => band.to === null);
  return <section aria-labelledby="rail-heading" className={beyond ? 'rail has-over' : 'rail'}>
    <div className="rail-head">
      <div><h2 id="rail-heading">Prices today</h2>
        <p className="rail-note">{condition
          ? `${count(bands.reduce((sum, band) => sum + band.drives, 0))} in stock, by item price per TB.`
          // Every condition: a drive sold in two is marked twice, so the marks are prices, not drives.
          : `${bands.reduce((sum, band) => sum + band.drives, 0).toLocaleString('en-US')} prices in stock: each drive’s lowest in each condition, by item price per TB.`}</p>
        <p className="rail-note">Each bar holds the drives in one price band and is as tall as there are drives in it; each doubling of price takes the same width.</p></div>
      {sold.length > 1 && <div role="group" aria-label="Condition" className="trend-choice segmented">
        {[{ value: null, label: 'All' }, ...sold].map(({ value, label: text }) => <button key={text} type="button" className="rail-choice"
          aria-pressed={value === condition} onClick={() => choose(value as Condition | null)}>{text}</button>)}</div>}
    </div>
    <p role="status" className="rail-readout"><span className="rail-label">{pointed !== null ? count(read.drives) : condition ? `Lowest ${conditionLabel(condition).toLowerCase()}` : 'Lowest in stock'}</span>
      <strong>{pointed === null ? `${price(read)} per TB` : reach(read)}</strong>
      <span className="rail-drive">{read.drives > 1 && pointed !== null ? `cheapest ${name(read)} at ${price(read)}`
        : read.to === null && pointed !== null ? `${name(read)} at ${price(read)}` : condition ? name(read) : `${name(read)}, ${conditionLabel(read.cheapest.condition)}`}</span></p>
    <div ref={track} role="group" aria-label="Drives by price per TB" className="rail-track">{bands.map((band, index) => <button key={band.index} type="button"
      className={['rail-mark', band.lowest && 'lowest', band.to === null && 'over'].filter(Boolean).join(' ')}
      style={{ '--fill': band.drives / most, ...(band.to !== null && { left: `${band.index / RAIL_BANDS * 100}%`, width: `${100 / RAIL_BANDS}%` }) } as CSSProperties}
      data-index={index} tabIndex={index === (stop ?? lowest) ? 0 : -1} aria-label={label(band)}
      onClick={() => onSelect(band.cheapest.key, band.cheapest.condition)} onKeyDown={event => move(event, index)}
      onMouseEnter={() => setPointed(index)} onMouseLeave={() => setPointed(null)} onFocus={() => setPointed(index)} onBlur={() => setPointed(null)} />)}</div>
    <div className="rail-axis" aria-hidden="true">{rail.ticks.map(tick => <span key={tick} style={{ left: `${along(rail, tick) * 100}%` }}>{rulerLabel(tick)}</span>)}
      {beyond && <span className="rail-more">More</span>}</div>
  </section>;
}
