type Errors = Record<string, string>;

type LoginValues = {
  email: string;
  password: string;
};

type RegisterValues = LoginValues & {
  fullName: string;
  confirmPassword: string;
  termsAccepted: boolean;
  privacyAccepted: boolean;
};

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateLoginForm(values: LoginValues): Errors {
  const errors: Errors = {};
  if (!emailPattern.test(values.email.trim())) {
    errors.email = 'Enter a valid email address.';
  }
  if (!values.password) {
    errors.password = 'Enter your password.';
  }
  return errors;
}

export function validateRegisterForm(values: RegisterValues): Errors {
  const errors = validateLoginForm(values);
  if (values.fullName.trim().length < 2) {
    errors.fullName = 'Enter your full name.';
  }
  if (values.password.length < 10) {
    errors.password = 'Use at least 10 characters.';
  } else if (
    ![...values.password].some((character) => /[A-Za-z]/.test(character)) ||
    ![...values.password].some((character) => /\d/.test(character))
  ) {
    errors.password = 'Include at least one letter and one number.';
  }
  if (values.password !== values.confirmPassword) {
    errors.confirmPassword = 'Passwords do not match.';
  }
  if (!values.termsAccepted) {
    errors.termsAccepted = 'Accept the Terms of Service to continue.';
  }
  if (!values.privacyAccepted) {
    errors.privacyAccepted = 'Accept the Privacy Policy to continue.';
  }
  return errors;
}
