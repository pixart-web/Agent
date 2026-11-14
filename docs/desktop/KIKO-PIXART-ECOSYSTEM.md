# Kiko in the Pixart ecosystem — foundation design

**Status:** design only. No live connector to another Pixart product was built, because no
product's integration API has been verified yet. Nothing here should be presented to users as
available.

## 1. Products in scope (to be audited before any connector)

| Product          | Known role                   | Integration contract status |
| ---------------- | ---------------------------- | --------------------------- |
| Web Content Flow | content production workflow  | not audited                 |
| CyberAudit       | security auditing            | not audited                 |
| SearchAnvil      | SEO / search tooling         | not audited                 |
| Nodera           | infrastructure control plane | not audited                 |

A connector may only be built after its product exposes a **versioned, documented API** with
scoped service credentials, and that contract is recorded in this file.

## 2. Principles

1. **No shared databases.** Products integrate through APIs and events only.
2. **Each product keeps its own authorization.** Kiko never bypasses it; it acts with a
   scoped identity the product issued.
3. **No mandatory coupling.** Kiko works without any other product; each connector is
   optional and fails closed.
4. **Governed writes.** Any write into another product is a Kiko tool with risk level,
   approval policy, idempotency key and audit trail, executed by the backend worker — never by
   a desktop client.
5. **No credentials in clients.** Connector secrets live in the Kiko backend secret store,
   encrypted like current integrations (`INTEGRATION_ENCRYPTION_KEY`).

## 3. Application registry (proposed backend model)

```
pixart_applications        (id, key, name, base_url, api_version, status, docs_url)
workspace_app_connections  (id, workspace_id, application_id, status, scopes[],
                            credential_ref, connected_by, connected_at, last_health_at)
```

Connection status vocabulary shown in the Integration Hub (desktop and web):
`available` · `connected` · `disconnected` · `requires_setup` · `unsupported` · `unavailable`.
The existing Integrations screen already reports real state for Gmail, Calendar, GitHub and
Codex; Pixart products will appear only once registered with a verified contract.

## 4. Identity and future SSO

- Today each product has its own accounts. Kiko desktop signs in to Kiko only.
- Target: a Pixart identity provider issuing OIDC tokens (Authorization Code + PKCE through
  the system browser for desktop, loopback or `kiko://` redirect). Products validate tokens
  and map `sub` + workspace claims to their own roles.
- Until then, product-to-product calls use per-workspace service credentials (OAuth client
  credentials or scoped API keys) issued by the target product.

## 5. Scoped permissions

Connector scopes are declared per product (`read:projects`, `write:content`, …) and granted
per workspace by a Kiko Owner/Admin. Kiko tools check the granted scope before proposing an
action; the target product enforces it again.

## 6. Inter-application events

- Transport: signed webhooks (HMAC, timestamp, replay window) into a Kiko inbox endpoint,
  persisted to an inbox table and processed idempotently by workers (mirrors the existing
  outbox pattern).
- Envelope: `{id, source_app, type, version, workspace_ref, occurred_at, data}`.
- Events feed the unified activity model and notifications (e.g. "CyberAudit finding
  requires approval").

## 7. Deep-link conventions

| Scheme / URL                           | Meaning                                 |
| -------------------------------------- | --------------------------------------- |
| `kiko://open/<dashboard path>`         | open a Kiko screen (implemented)        |
| `kiko://verify-email?token=…`          | email verification (implemented)        |
| `kiko://reset-password?token=…`        | password reset (implemented)            |
| `kiko://invite?token=…`                | workspace invitation (implemented)      |
| `kiko://app/<app-key>/<resource>/<id>` | reserved: open a linked Pixart resource |

Links only navigate; they never perform an action without user interaction in the app.

## 8. Next steps

1. Audit each product's API (auth, versioning, rate limits, tenancy) and record it here.
2. Add the registry tables and an admin-only registration endpoint.
3. Build the first read-only connector behind a feature flag; add write tools only with
   approval policies.
