# Kiko security review

Reviewed on 2026-10-14 against the OWASP ASVS/API Security categories and the
project's Python/FastAPI and TypeScript/Next.js attack surface. This is a
repository review, not a certification or an infrastructure penetration test.

## Executive summary

No known critical or high application/dependency vulnerability remains in the
reviewed release candidate. The review found vulnerable framework constraints
and frontend packages; both were remediated and the Python and pnpm production
audits now report no known vulnerabilities. A defence-in-depth CSP limitation
remains low severity and is documented below.

Assumptions: the application is internet-facing behind a TLS reverse proxy;
PostgreSQL and Redis are private; Kiko is multi-tenant; integrations remain
disabled until explicit credentials and account/repository allowlists exist; and
the Codex runner executes in a separately isolated worker. Runtime validation of
the proxy, firewall, secret manager and container host remains a staging gate.

## Remediated findings

### SEC-001 — Vulnerable web and API dependency constraints (Critical)

- Location: `apps/web/package.json`, `pnpm-workspace.yaml`,
  `apps/api/pyproject.toml`.
- Evidence: the initial audit reported two critical Next.js advisories, seven
  high transitive advisories, and vulnerable Cryptography/Starlette versions.
- Impact: depending on host and enabled processing paths, unauthenticated code
  execution, arbitrary file reads, denial of service, or vulnerable crypto/parser
  behavior.
- Fix: upgraded Next.js to the patched 15.5 line, overrode patched Sharp,
  PostCSS, Nanoid and source-map-js versions, and upgraded FastAPI, Starlette,
  Cryptography and pytest to patched compatible lines.
- Verification: `pnpm audit --prod` and `pip-audit` both return no known
  vulnerabilities; all backend/frontend tests and the production web build pass.

### SEC-002 — Production OpenAPI schema remained public (Medium)

- Location: `apps/api/app/main.py`, FastAPI construction.
- Evidence: production disabled `/docs` and `/redoc` but left the default
  `/openapi.json` route enabled.
- Impact: unnecessary disclosure of privileged route and schema details.
- Fix: production now also sets `openapi_url=None`.

### SEC-003 — OpenAI key was not a redacted settings type (Medium)

- Location: `apps/api/app/core/config.py` and
  `apps/api/app/ai/provider_factory.py`.
- Evidence: `openai_api_key` used `str | None`, unlike other credentials.
- Impact: accidental disclosure through settings representation or diagnostics.
- Fix: the setting is a Pydantic `SecretStr` and is unwrapped only at the provider
  boundary.

### SEC-004 — Missing browser response policy (Medium)

- Location: `apps/web/next.config.ts`.
- Evidence: no frontend CSP, clickjacking, MIME-sniffing, referrer, or browser
  capability policy was configured.
- Impact: weaker containment if an injection bug or third-party content issue is
  introduced.
- Fix: global CSP, `frame-ancestors`, `X-Frame-Options`,
  `X-Content-Type-Options`, `Referrer-Policy`, and `Permissions-Policy` headers.

## Residual findings

### SEC-005 — CSP permits inline scripts/styles (Low)

- Location: `apps/web/next.config.ts`, `headers()`.
- Evidence: `script-src` and `style-src` include `'unsafe-inline'` to support the
  current Next.js rendering model.
- Impact: CSP cannot fully contain a future HTML injection flaw, although React
  escaping, the absence of dangerous HTML sinks, `object-src 'none'`,
  `frame-ancestors 'none'`, and same-origin resource policies reduce exposure.
- Recommendation: migrate to per-request nonces when the Next.js delivery stack
  supports the required dynamic rendering trade-off. Do not add `unsafe-eval`.
- Release decision: accepted low residual risk; not a critical/high blocker.

## Control coverage

- Authentication: Argon2 password hashing, short-lived bearer access tokens,
  hashed/rotated refresh tokens, secure production cookie requirements, one-shot
  verification/reset tokens, session revocation and rate limiting.
- Authorization: server-side workspace membership checks, object-level queries,
  owner/admin boundaries, separation of duties, approval payload fingerprints,
  and PostgreSQL cross-workspace regression coverage.
- OAuth/external writes: short-lived one-shot state, encrypted credentials,
  account/domain allowlists, disabled-by-default writes, approval and idempotency.
- Injection/upload: schema-driven inputs, SQLAlchemy parameters, no shell mode in
  runner commands, bounded uploads, file-type parsing without execution, safe CSV
  output, no frontend raw-HTML/eval/message sinks found.
- Infrastructure: trusted hosts, strict configured CORS, production fail-fast
  settings, private metrics authentication, structured request IDs, bounded
  agents/retries/timeouts, checksummed backup/restore, and controlled runner
  environment.
- Supply chain: patched dependency ranges plus clean Python and pnpm audits as of
  the review date. CI must repeat both audits because advisory status changes.

## Staging-only validations still required

The repository cannot establish TLS/proxy behavior, network segmentation, secret
manager controls, container isolation, alert delivery, or real Google provider
permissions. Validate those controls in isolated staging. Gmail and Calendar
must remain disabled in real mode until explicitly authorized test accounts pass
the provider checklist; a synthetic demo must be labelled as such.
