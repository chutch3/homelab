import { describe, expect, it } from 'vitest';
import { validationError } from '../../src/api';

describe('API validation error translation', () => {
  it('preserves body field paths and messages', () => {
    const error = validationError([
      { loc: ['body', 'title'], msg: 'Enter a listing title.' },
      { loc: ['body', 'observation', 'shipping_cents'], msg: 'Shipping must be non-negative.' },
    ]);
    expect(error?.fields).toEqual({
      title: 'Enter a listing title.',
      'observation.shipping_cents': 'Shipping must be non-negative.',
    });
  });

  it.each([null, 'Bad request', [null], [{ loc: ['header', 'idempotency-key'], msg: 'Missing key' }]])(
    'leaves non-field errors for the normal error handler', detail => {
      expect(validationError(detail)).toBeNull();
    },
  );
});
