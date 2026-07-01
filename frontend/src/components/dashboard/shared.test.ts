import { describe, expect, it } from 'vitest';

import { formatPct, formatSignedByCurrency, formatSignedTWD } from './shared';

describe('dashboard shared formatters', () => {
  it('adds explicit signs to TWD gain and loss values', () => {
    expect(formatSignedTWD(1250)).toBe('+NT$1,250');
    expect(formatSignedTWD(-1250)).toBe('-NT$1,250');
    expect(formatSignedTWD(0)).toBe('+NT$0');
  });

  it('adds explicit signs to local-currency gain and loss values', () => {
    expect(formatSignedByCurrency(88.5, 'USD')).toBe('+US$88.5');
    expect(formatSignedByCurrency(-88.5, 'USD')).toBe('-US$88.5');
    expect(formatSignedByCurrency(0, 'TWD')).toBe('+NT$0');
  });

  it('keeps percentage formatting signed for positive and negative values', () => {
    expect(formatPct(12.34)).toBe('+12.34%');
    expect(formatPct(-12.34)).toBe('-12.34%');
  });
});
