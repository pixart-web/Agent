# Authentication

## Model

Users are persisted with normalized lowercase email, Argon2id password hash, active
and superuser flags, and UTC timestamps. Public schemas never contain
`password_hash`. Refresh-token rows contain only a SHA-256 hash of the opaque token,
its user and rotation family, expiry and revocation timestamps, replacement link, and
optional request metadata.

New accounts also persist versioned Terms and Privacy acceptance timestamps. Existing
pre-migration accounts are marked with the explicit `legacy` version so the migration
does not silently lock out operators.

## Verification and recovery

Registration returns the same HTTP 202 response for new and existing addresses, so it
cannot be used to enumerate accounts. New accounts are unverified by default and
cannot log in or use protected endpoints until verification completes.

Email-verification and password-reset secrets are random opaque values. Only SHA-256
hashes are stored in `account_tokens`; tokens are short-lived, single-use, and a new
token consumes previous active tokens for the same purpose. Password reset revokes all
refresh sessions. Recovery requests return the same public response for missing,
inactive, unverified, and eligible accounts.

Authenticated users can update their normalized display name and change their
password after proving the current password. A password change revokes every refresh
session and clears the current cookie, requiring a fresh sign-in.

The raw secret is stored only inside a Fernet-encrypted transactional-email outbox
payload. A separate dispatcher decrypts and sends bounded batches through configured
SMTP, records only a bounded error class, and stops retrying after the configured
attempt limit. Production refuses to start with required verification but without a
transactional email provider.

## Passwords and access tokens

Passwords require at least 10 characters, one letter, and one number. Argon2id is
provided by `argon2-cffi`; no custom cryptography is used.

Access tokens are HS256 JWTs with only `sub`, `iat`, `exp`, and `type=access`. They
default to 15 minutes and are validated for signature, required claims, expiry, and
type. The frontend retains them only in memory—never `localStorage` or
`sessionStorage`.

## Refresh cookies and rotation

Refresh tokens are generated with a cryptographically secure random source, are
opaque rather than JWTs, and default to 30 days. The raw value exists only at issuance
and in the browser cookie:

- name: `agent_refresh_token`;
- `HttpOnly=true`;
- `Secure` and `SameSite` from settings;
- path: `/api/v1/auth`;
- domain optional;
- lifetime equal to the token expiry.

On refresh the service hashes and locks the presented row, confirms validity, creates
a replacement in the same family, revokes the predecessor, links
`replaced_by_id`, issues a new access token, and replaces the cookie in one
transaction.

Presenting an already-revoked refresh token is treated as reuse: every active token in
its family is revoked and the request receives a generic HTTP 401. Expired, missing,
unknown, or inactive-user refreshes receive the same public outcome. Logout revokes
the current token when present, always clears the cookie, and is idempotent.

## Protected requests

```text
Authorization: Bearer <access token>
    -> JWT validation
    -> UserRepository
    -> active-user validation
    -> protected endpoint
```

`get_current_user`, `get_current_active_user`, and the prepared
`get_current_superuser` dependencies centralize this flow. `/me` returns 401 for
missing or invalid authentication and 403 for an inactive user.

## Frontend flow

Registration redirects to the verification page. Login receives an access token and
refresh cookie. When the protected dashboard starts, the client calls refresh and
then `/me`. Unauthorized API requests
perform at most one renewal attempt. Concurrent requests share one refresh promise,
preventing rotation races and retry loops. Logout clears backend and in-memory state;
failed renewal redirects to `/login`. Password confirmation is validated only in the
browser and is not sent to the API.

## Rate limiting

Register, login, and refresh use a Redis fixed window keyed by endpoint and a SHA-256
digest of the client IP. Limits and window are configurable. Rejected calls return
HTTP 429 and `Retry-After`. Redis failures default to fail-open for development so a
local outage does not block authentication. Set
`AUTH_RATE_LIMIT_FAIL_OPEN=false` for fail-closed production behavior.

## Configuration

```env
APP_ENV=development
WEB_ORIGINS=http://localhost:3000
AUTH_SECRET_KEY=replace-with-at-least-32-random-characters
AUTH_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax
AUTH_COOKIE_DOMAIN=
AUTH_RATE_LIMIT_ENABLED=true
AUTH_RATE_LIMIT_REQUESTS=10
AUTH_RATE_LIMIT_WINDOW_SECONDS=60
AUTH_RATE_LIMIT_FAIL_OPEN=true
AUTH_CLEANUP_RETENTION_DAYS=7
AUTH_REQUIRE_EMAIL_VERIFICATION=true
EMAIL_VERIFICATION_EXPIRE_MINUTES=60
PASSWORD_RESET_EXPIRE_MINUTES=30
ACCOUNT_TOKEN_RESEND_COOLDOWN_SECONDS=60
LEGAL_TERMS_VERSION=2026-10-10
LEGAL_PRIVACY_VERSION=2026-10-10
PUBLIC_WEB_URL=https://kiko.example.com
TRANSACTIONAL_EMAIL_ENABLED=true
TRANSACTIONAL_EMAIL_FROM=Kiko <no-reply@example.com>
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_STARTTLS=true
```

Expiries and limits must be positive, the algorithm is restricted to HS256, and
SameSite must be `lax`, `strict`, or `none`. SameSite `none` requires a secure cookie.
Production refuses the documented development secret and requires
`AUTH_COOKIE_SECURE=true`. `WEB_ORIGINS` accepts a comma-separated allowlist; CORS
credentials are enabled and wildcard origins are not used.

## Sessions and maintenance

Authenticated users can list active refresh sessions, see which session matches the
current cookie, revoke one owned session, or revoke all sessions. Session identifiers
are always scoped to the authenticated user. The Settings screen exposes profile,
password-change, and selective session-revocation workflows.

Run `make cleanup-auth` or:

```bash
cd apps/api
python -m app.scripts.cleanup_refresh_tokens
```

The command removes expired tokens and tokens revoked before the configured retention
period. Social login, MFA, workspace-wide authorization, and administrative user
management remain future work.
