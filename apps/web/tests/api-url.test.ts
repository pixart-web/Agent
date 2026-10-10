import { describe, expect, it } from 'vitest';

import { resolveApiBaseUrl } from '../lib/api-url';

describe('API base URL', () => {
  it('forces same-origin requests in production', () => {
    expect(resolveApiBaseUrl('production', 'https://wrong.example')).toBe('');
  });

  it('supports a separate local API during development', () => {
    expect(resolveApiBaseUrl('development', 'http://localhost:8000/')).toBe(
      'http://localhost:8000',
    );
  });

  it('uses the conventional local API when development is unconfigured', () => {
    expect(resolveApiBaseUrl('development', undefined)).toBe(
      'http://localhost:8000',
    );
  });
});
