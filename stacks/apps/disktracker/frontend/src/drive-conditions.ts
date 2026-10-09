import type { Condition, ListingSummary } from './api';
import { conditions, dollars } from './listing-display';

/** One condition a drive is offered in: how many offers it has, how many of them are in stock,
 * and the lowest total among those (null when none is). */
export type ConditionChoice = { condition: Condition; label: string; offers: number; inStock: number; lowest: number | null };

/** The conditions a drive is offered in, in the usual order. A new drive and a refurbished one
 * are different things to buy, so each condition is shown, compared and charted on its own. */
export function conditionChoices(listings: ListingSummary[]): ConditionChoice[] {
  return conditions.flatMap(({ value, label }) => {
    const offers = listings.filter(listing => listing.condition === value);
    if (!offers.length) return [];
    const stocked = offers.filter(listing => listing.latest.in_stock).map(listing => listing.latest.total_cents);
    return [{ condition: value as Condition, label, offers: offers.length, inStock: stocked.length, lowest: stocked.length ? Math.min(...stocked) : null }];
  });
}

/** What a condition costs now, so conditions can be compared without switching between them. */
export function priceLabel({ lowest, inStock }: ConditionChoice): string {
  if (lowest === null) return 'Out of stock';
  return inStock > 1 ? `from ${dollars(lowest)}` : dollars(lowest);
}

/** The condition a drive opens on: the one asked for when the drive is offered in it, else the
 * cheapest in stock, else the first. */
export function startingCondition(choices: ConditionChoice[], preferred?: Condition): Condition {
  if (choices.some(choice => choice.condition === preferred)) return preferred!;
  const stocked = choices.filter(choice => choice.lowest !== null);
  return (stocked.length ? stocked.reduce((best, choice) => choice.lowest! < best.lowest! ? choice : best) : choices[0]).condition;
}
