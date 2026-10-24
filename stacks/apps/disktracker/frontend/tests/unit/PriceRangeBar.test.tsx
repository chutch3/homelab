import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { PriceRangeBar } from '../../src/PriceRangeBar';
import type { PriceRange } from '../../src/api';

afterEach(cleanup);

const moved: PriceRange = { today: 18000, low: 17000, high: 19000, average: 18222, days: 90 };
const show = (range: PriceRange, days = 90) => render(<PriceRangeBar range={range} days={days} />);
const part = (name: string) => screen.getByRole('img').querySelector<HTMLElement>(`.range-${name}`)!;

describe('PriceRangeBar', () => {
  it('draws how far above its lowest price a drive has been, is on average and is today, on a scale of 30%, and says it in words', () => {
    show(moved);
    expect(screen.getByRole('img')).toHaveAccessibleName('Today $180.00, 5.9% above the lowest. Over 90 days: lowest $170.00, average $182.22, highest $190.00.');
    // $190 is 11.8% above $170, so the line runs 39.2% of the way across; the average 7.2% and today 5.9% sit along it.
    expect(part('span').style.width).toBe('39.2%');
    expect(part('average').style.left).toBe('24%');
    expect(part('today').style.left).toBe('19.6%');
    expect(screen.getByText('+5.9% above its low')).toBeVisible();
    expect(screen.getByRole('img')).not.toHaveClass('short');
    expect(part('span')).not.toHaveClass('over');
  });

  it('says where the price stands in words first, the picture after', () => {
    show(moved);
    const words = screen.getByText('+5.9% above its low');
    expect(words.compareDocumentPosition(screen.getByRole('img')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('says a drive is at its low when today is the lowest it has been', () => {
    show({ ...moved, today: 17000 });
    expect(screen.getByText('At its lowest')).toBeVisible();
    expect(part('today').style.left).toBe('0%');
  });

  it('leaves the line open at the full width when the price has been more than 30% above its low', () => {
    show({ today: 15000, low: 10000, high: 20000, average: 14000, days: 90 });
    expect(part('span').style.width).toBe('100%');
    expect(part('span')).toHaveClass('over');
    expect(part('today').style.left).toBe('100%');
    expect(part('average').style.left).toBe('100%');
    expect(screen.getByText('+50.0% above its low')).toBeVisible();
  });

  it('marks a drive with fewer days of prices than the period, and says how many', () => {
    show({ ...moved, days: 12 });
    expect(screen.getByRole('img')).toHaveClass('short');
    expect(screen.getByRole('img')).toHaveAccessibleName('Today $180.00, 5.9% above the lowest. Over 12 days: lowest $170.00, average $182.22, highest $190.00.');
    expect(screen.getByText('+5.9% above its low, tracked 12 days')).toBeVisible();
  });

  it('says in words alone that a price has not changed, or that the drive is new', () => {
    const { unmount } = show({ today: 20000, low: 20000, high: 20000, average: 20000, days: 90 });
    expect(screen.getByText('No change')).toBeVisible();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    unmount();
    show({ today: 20000, low: 20000, high: 20000, average: 20000, days: 3 });
    expect(screen.getByText('Tracked for 3 days')).toBeVisible();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('counts a single day as a day, and says today for a drive first priced today', () => {
    const { unmount } = show({ today: 20000, low: 20000, high: 20000, average: 20000, days: 1 });
    expect(screen.getByText('Tracked for 1 day')).toBeVisible();
    unmount();
    show({ today: 20000, low: 20000, high: 20000, average: 20000, days: 0 });
    expect(screen.getByText('First seen today')).toBeVisible();
    cleanup();
    show({ today: 18000, low: 17000, high: 19000, average: 18222, days: 1 });
    expect(screen.getByRole('img')).toHaveAccessibleName('Today $180.00, 5.9% above the lowest. Over 1 day: lowest $170.00, average $182.22, highest $190.00.');
    expect(screen.getByText('+5.9% above its low, tracked 1 day')).toBeVisible();
  });

  it('shows nothing for a drive no store has in stock today', () => {
    const { container } = show({ ...moved, today: null });
    expect(container).toBeEmptyDOMElement();
  });
});
