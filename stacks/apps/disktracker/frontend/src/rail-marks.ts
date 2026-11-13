import type { Condition } from './api';

/** A drive in one condition, placed by what a terabyte of it costs today: the lowest item price any
 * store with it in stock asks, in cents. lowest marks the cheapest of those checked recently. */
export type RailMark = { key: string; condition: Condition; title: string; capacityGb: number; perTb: number; lowest: boolean };

/** The drives of one condition whose prices fall together on the rail, in cents per terabyte from
 * `from` up to `to`; past the rail's end there is no `to`. index counts the bands from the cheap
 * end; cheapest is the one to name and open. */
export type RailBand = { condition: Condition; index: number; from: number; to: number | null; drives: number; cheapest: RailMark; lowest: boolean };
/** A rail from low to high cents per terabyte, named at each of ticks, with its bands cheapest first. */
export type Rail = { low: number; high: number; ticks: number[]; bands: RailBand[] };

/** How many bands the rail is cut into: few enough for each to be a bar wide enough to point at. */
export const RAIL_BANDS = 40;
/** The rail reaches this share of the drives; the few far dearer are gathered past its end. */
const REACH = 0.99;
/** The round figures a rail may end on, and the fewer it is named at, in each tenfold. */
const ENDS = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8], NAMED = [1, 2, 5];
/** A rail is named this many times at least, and this many at most. */
const FEWEST_TICKS = 4, MOST_TICKS = 10;

/** The round amounts of cents from a cent up to at least `reach`, each tenfold cut by `figures`. */
function rounds(figures: number[], reach: number): number[] {
  const found: number[] = [];
  for (let scale = 1; (found[found.length - 1] ?? 0) < reach; scale *= 10) found.push(...figures.map(figure => figure * scale));
  return found;
}

/** Where a price in cents falls along the rail, from 0 at its cheap end to 1 at its dear one. Each
 * doubling of price takes the same room: drives are sold from a few dollars a terabyte to thousands,
 * and evenly spaced dollars would crowd every cheap one into a corner. */
export function along({ low, high }: Pick<Rail, 'low' | 'high'>, cents: number): number {
  return Math.log(cents / low) / Math.log(high / low);
}

/** The rail the marks (cheapest first) are drawn on, or null when there are none. One drive far
 * dearer than the rest would set a scale every other drive is lost on, so the rail ends where all
 * but the dearest hundredth are. */
export function rail(marks: RailMark[]): Rail | null {
  if (!marks.length) return null;
  const cheapest = Math.max(1, marks[0].perTb), reach = Math.max(cheapest, marks[Math.ceil(marks.length * REACH) - 1].perTb);
  const ends = rounds(ENDS, reach);
  const low = [...ends].reverse().find(end => end <= cheapest) ?? 1, high = ends.find(end => end >= reach && end > low)!;
  const named = rounds(NAMED, high).filter(tick => tick >= low && tick <= high);
  // Too few round figures between its ends: name it every even step instead. Too many: every tenfold.
  const step = rounds(NAMED, high).find(size => (high - low) / size <= 6)!;
  const ticks = named.length < FEWEST_TICKS ? Array.from({ length: Math.floor(high / step) - Math.ceil(low / step) + 1 }, (_, index) => (Math.ceil(low / step) + index) * step)
    : named.length > MOST_TICKS ? named.filter(tick => Number.isInteger(Math.log10(tick))) : named;
  const edge = (index: number) => low * (high / low) ** (index / RAIL_BANDS);
  const bands = new Map<string, RailBand>();
  for (const mark of marks) {
    const over = mark.perTb > high;
    const index = over ? RAIL_BANDS : Math.max(0, Math.min(RAIL_BANDS - 1, Math.floor(along({ low, high }, mark.perTb) * RAIL_BANDS)));
    const id = `${mark.condition}|${index}`, band = bands.get(id);
    if (band) { band.drives += 1; band.lowest ||= mark.lowest; }
    else bands.set(id, { condition: mark.condition, index, from: over ? high : edge(index), to: over ? null : edge(index + 1), drives: 1, cheapest: mark, lowest: mark.lowest });
  }
  return { low, high, ticks, bands: [...bands.values()] };
}

/** The bands to draw, cheapest first: one condition's, or every condition's with the drives of a
 * band counted together and its cheapest drive, whatever its condition, the one named. */
export function railBands({ bands }: Rail, condition: Condition | null): RailBand[] {
  if (condition) return bands.filter(band => band.condition === condition).sort((a, b) => a.index - b.index);
  const together = new Map<number, RailBand>();
  for (const band of bands) {
    const held = together.get(band.index);
    if (!held) together.set(band.index, { ...band });
    else Object.assign(held, { drives: held.drives + band.drives, lowest: held.lowest || band.lowest, ...(band.cheapest.perTb < held.cheapest.perTb && { cheapest: band.cheapest, condition: band.condition }) });
  }
  return [...together.values()].sort((a, b) => a.index - b.index);
}
