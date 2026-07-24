import { describe, expect, it } from 'vitest';

import {
  validateLoginForm,
  validateRegisterForm,
} from '../lib/form-validation';

describe('authentication form validation', () => {
  it('accepts a valid login form', () => {
    expect(
      validateLoginForm({
        email: 'user@example.com',
        password: 'securePassword123',
      }),
    ).toEqual({});
  });

  it('validates registration fields and password confirmation', () => {
    const errors = validateRegisterForm({
      fullName: '',
      email: 'invalid',
      password: 'short',
      confirmPassword: 'different',
    });

    expect(errors.fullName).toBeDefined();
    expect(errors.email).toBeDefined();
    expect(errors.password).toBeDefined();
    expect(errors.confirmPassword).toBe('Passwords do not match.');
  });
});
