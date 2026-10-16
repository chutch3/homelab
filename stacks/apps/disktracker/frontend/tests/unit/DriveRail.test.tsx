import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DriveRail } from '../../src/DriveRail';
import { rail, type RailMark } from '../../src/rail-marks';

afterEach(cleanup);

const marks: RailMark[] = [
  { key: 'drive:exos', condition: 'manufacturer_recertified', title: 'Exos X18', capacityGb: 18000, perTb: 1000, lowest: true },
  { key: 'drive:exos', condition: 'new', title: 'Exos X18', capacityGb: 18000, perTb: 1600, lowest: false },
  { key: 'drive:gold', condition: 'new', title: 'WD Gold', capacityGb: 22000, perTb: 1950, lowest: false },
];
/** Two drives a few cents apart, so in one band, and a third far dearer than a hundred others, so past the rail's end. */
const crowded: RailMark[] = [
  { key: 'drive:ultrastar', condition: 'new', title: 'Ultrastar', capacityGb: 16000, perTb: 1000, lowest: true },
  { key: 'drive:ironwolf', condition: 'new', title: 'IronWolf', capacityGb: 12000, perTb: 1005, lowest: false },
  ...Array.from({ length: 100 }, (_, index): RailMark => ({ key: `drive:${index}`, condition: 'used', title: `Drive ${index}`, capacityGb: 8000, perTb: 1100 + index * 9, lowest: false })),
  { key: 'drive:tape', condition: 'new', title: 'LTO-8 tape drive', capacityGb: 8, perTb: 63937500, lowest: false },
];
const show = (onSelect = vi.fn(), drawn = marks) => { const shown = render(<DriveRail rail={rail(drawn)} onSelect={onSelect} />); return { onSelect, ...shown }; };
const mark = (name: RegExp) => within(screen.getByRole('group', { name: 'Drives by price per TB' })).getByRole('button', { name });
const bars = () => within(screen.getByRole('group', { name: 'Drives by price per TB' })).getAllByRole('button');
const readout = () => screen.getByRole('status').textContent;

describe('DriveRail', () => {
  it('counts every drive along one ruler of dollars per terabyte, all conditions together, and reads out the cheapest', () => {
    show();
    expect(screen.getByRole('region', { name: 'Prices today' })).toBeVisible();
    expect(bars().map(button => button.getAttribute('aria-label')))
      .toEqual(['Exos X18 18 TB, recertified, $10.00 per TB', 'Exos X18 18 TB, new, $16.00 per TB', 'WD Gold 22 TB, new, $19.50 per TB']);
    // The ruler runs from $10 to $20 in forty bands: $16 falls in the twenty-eighth.
    expect(mark(/^Exos X18 18 TB, new/).style.left).toBe('67.5%');
    expect(mark(/^Exos X18 18 TB, recertified/).style.left).toBe('0%');
    expect(mark(/^Exos X18 18 TB, recertified/)).toHaveClass('lowest');
    expect(readout()).toBe('Lowest in stock' + '$10.00 per TB' + 'Exos X18 18 TB, Recertified');
  });

  it('shows one condition alone when it is chosen, and all of them again after', async () => {
    const user = userEvent.setup();
    show();
    const conditions = within(screen.getByRole('group', { name: 'Condition' }));
    // Only the conditions there are drives in.
    expect(conditions.getAllByRole('button').map(button => [button.textContent, button.getAttribute('aria-pressed')]))
      .toEqual([['All', 'true'], ['New', 'false'], ['Recertified', 'false']]);
    await user.click(conditions.getByRole('button', { name: 'New' }));
    expect(conditions.getByRole('button', { name: 'New' })).toHaveAttribute('aria-pressed', 'true');
    expect(bars().map(button => button.getAttribute('aria-label'))).toEqual(['Exos X18 18 TB, new, $16.00 per TB', 'WD Gold 22 TB, new, $19.50 per TB']);
    expect(readout()).toBe('Lowest new' + '$16.00 per TB' + 'Exos X18 18 TB');
    await user.click(conditions.getByRole('button', { name: 'All' }));
    expect(bars()).toHaveLength(3);
  });

  it('offers no choice of condition when every drive is in one', () => {
    show(vi.fn(), marks.slice(1));
    expect(screen.queryByRole('group', { name: 'Condition' })).not.toBeInTheDocument();
  });

  it('names the ruler at a few round prices', () => {
    const { container } = show();
    expect([...container.querySelectorAll('.rail-axis span')].map(tick => tick.textContent)).toEqual(['$10', '$12', '$14', '$16', '$18', '$20']);
  });

  it('names the ruler at each tenfold when prices are very far apart', () => {
    const far: RailMark[] = [
      { key: 'drive:exos', condition: 'new', title: 'Exos X18', capacityGb: 18000, perTb: 119, lowest: true },
      { key: 'drive:tape', condition: 'new', title: 'LTO-8 tape drive', capacityGb: 8, perTb: 63937500, lowest: false },
    ];
    const { container } = show(vi.fn(), far);
    expect([...container.querySelectorAll('.rail-axis span')].map(tick => tick.textContent))
      .toEqual(['$1', '$10', '$100', '$1,000', '$10,000', '$100,000']);
  });

  it('draws drives whose prices fall together as one bar, as tall as there are drives in it, naming how many and the cheapest', async () => {
    const { onSelect } = show(vi.fn(), crowded);
    const together = mark(/^2 drives, \$10\.00/);
    expect(together).toHaveAccessibleName('2 drives, $10.00 to $10.17 per TB, cheapest Ultrastar 16 TB at $10.00');
    expect(together).toHaveClass('lowest');
    // Used drives nine cents apart: the fullest band is the tallest bar, and a band of two is that share of it.
    const fills = bars().map(bar => Number(bar.style.getPropertyValue('--fill')));
    expect(Math.max(...fills)).toBe(1);
    const most = Math.max(...bars().map(bar => Number(/^(\d+) drives/.exec(bar.getAttribute('aria-label')!)?.[1] ?? 1)));
    expect(Number(together.style.getPropertyValue('--fill'))).toBeCloseTo(2 / most, 10);
    await userEvent.hover(together);
    expect(readout()).toBe('2 drives' + '$10.00 to $10.17 per TB' + 'cheapest Ultrastar 16 TB at $10.00');
    await userEvent.click(together);
    expect(onSelect).toHaveBeenCalledExactlyOnceWith('drive:ultrastar', 'new');
  });

  it('gathers the drives far dearer than the rest past the end of the ruler, under More', async () => {
    const { container } = show(vi.fn(), crowded);
    // The ruler ends at $20, where all but the dearest hundredth of drives are.
    expect([...container.querySelectorAll('.rail-axis span')].map(tick => tick.textContent)).toEqual(['$10', '$12', '$14', '$16', '$18', '$20', 'More']);
    const beyond = mark(/^LTO-8 tape drive 8 GB, new, \$639,375\.00 per TB$/);
    expect(beyond).toHaveClass('over');
    expect(beyond.style.left).toBe('');
    await userEvent.hover(beyond);
    expect(readout()).toBe('1 drive' + 'More than $20.00 per TB' + 'LTO-8 tape drive 8 GB at $639,375.00');
  });

  it('says in a line what is counted', () => {
    show(vi.fn(), crowded);
    expect(screen.getByText('103 prices in stock: each drive’s lowest in each condition, by item price per TB.')).toBeVisible();
    expect(screen.getByText('Each bar holds the drives in one price band and is as tall as there are drives in it; each doubling of price takes the same width.')).toBeVisible();
  });

  it('reads out the bar pointed at or focused, and the cheapest again after', async () => {
    const user = userEvent.setup();
    show();
    await user.hover(mark(/^WD Gold/));
    expect(readout()).toBe('1 drive' + '$19.50 per TB' + 'WD Gold 22 TB, New');
    await user.unhover(mark(/^WD Gold/));
    expect(readout()).toMatch(/^Lowest in stock/);
  });

  it('is one stop for the Tab key among its bars, with the arrow keys moving along them cheapest first', async () => {
    const user = userEvent.setup();
    show(vi.fn(), marks.slice(1));
    await user.tab();
    expect(mark(/^Exos X18 18 TB, new/)).toHaveFocus();
    expect(readout()).toBe('1 drive' + '$16.00 per TB' + 'Exos X18 18 TB, New');
    await user.keyboard('{End}');
    expect(mark(/^WD Gold/)).toHaveFocus();
    await user.keyboard('{ArrowRight}{ArrowLeft}{Home}');
    expect(mark(/^Exos X18 18 TB, new/)).toHaveFocus();
    await user.tab();
    expect(document.body).toHaveFocus();
  });

  it('opens a drive on the condition of the bar chosen', async () => {
    const { onSelect } = show();
    await userEvent.click(mark(/^Exos X18 18 TB, new/));
    expect(onSelect).toHaveBeenCalledExactlyOnceWith('drive:exos', 'new');
  });

  it('says so when no drive is in stock', () => {
    render(<DriveRail rail={rail([])} onSelect={() => {}} />);
    expect(screen.getByText('No drive is in stock.')).toBeVisible();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
