import { describe, expect, it } from 'vitest';
import { conditionChoices, priceLabel, startingCondition } from '../../src/drive-conditions';
import type { Condition } from '../../src/api';
import { makeListing } from '../fixtures/listings';

const offer = (id: string, condition: Condition, total: number, inStock = true) =>
  makeListing(id, { condition }, { total_cents: total, in_stock: inStock });

describe('the conditions a drive is offered in', () => {
  const listings = [
    offer('used', 'used', 30000), offer('refurbished-a', 'refurbished', 48900), offer('new', 'new', 45000, false),
    offer('refurbished-b', 'refurbished', 47000), offer('refurbished-sold-out', 'refurbished', 40000, false),
  ];

  it('lists them in the usual order, each with its offers and the lowest total in stock', () => {
    expect(conditionChoices(listings)).toEqual([
      { condition: 'new', label: 'New', offers: 1, inStock: 0, lowest: null },
      { condition: 'refurbished', label: 'Refurbished', offers: 3, inStock: 2, lowest: 47000 },
      { condition: 'used', label: 'Used', offers: 1, inStock: 1, lowest: 30000 },
    ]);
    expect(conditionChoices([])).toEqual([]);
  });

  it('says what each costs now: its price, the lowest of several, or that it is out of stock', () => {
    expect(conditionChoices(listings).map(priceLabel)).toEqual(['Out of stock', 'from $470.00', '$300.00']);
  });

  it('starts on the condition asked for, else the cheapest in stock, else the first', () => {
    const choices = conditionChoices(listings);
    expect(startingCondition(choices, 'refurbished')).toBe('refurbished');
    expect(startingCondition(choices)).toBe('used');
    // A condition the drive is not offered in cannot be started on.
    expect(startingCondition(choices, 'manufacturer_recertified')).toBe('used');
    expect(startingCondition(conditionChoices([offer('new', 'new', 45000, false), offer('used', 'used', 30000, false)]))).toBe('new');
  });
});
