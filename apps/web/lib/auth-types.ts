export type User = {
  id: string;
  email: string;
  full_name: string;
  language: string;
  timezone: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
  email_verified_at: string | null;
  active_workspace_id: string | null;
  onboarding_step: number;
  onboarding_completed_at: string | null;
  mfa_enabled?: boolean;
};

export type OnboardingState = {
  step: number;
  completed_at: string | null;
  workspace_id: string;
  company_name: string;
  company_description: string | null;
  primary_objectives: string[];
  /** False for members of someone else's workspace: the profile is shown read-only. */
  can_edit_company: boolean;
};

export type AuthResponse = {
  access_token: string;
  token_type: 'bearer';
  user: User;
};

export type AccessTokenResponse = {
  access_token: string;
  token_type: 'bearer';
};

export type Session = {
  id: string;
  created_at: string;
  expires_at: string;
  user_agent: string | null;
  ip_address: string | null;
  current: boolean;
};

export type MfaStatus = {
  enabled: boolean;
  enabled_at: string | null;
  recovery_codes_remaining: number;
  setup_pending: boolean;
};

export type MfaSetup = { secret: string; otpauth_uri: string };

/** Login result: signed in, or a second step is needed. */
export type LoginResult = { mfaToken: string | null };
