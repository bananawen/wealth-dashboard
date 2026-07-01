import { describe, expect, it } from 'vitest';
import { apiSlice } from '../store/apiSlice';

describe('frontend smoke', () => {
  it('configures the RTK Query API slice', () => {
    expect(apiSlice.reducerPath).toBe('api');
  });
});
