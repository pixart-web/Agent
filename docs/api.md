# API guide

The FastAPI service is rooted at `/api/v1`. Production intentionally disables the interactive
OpenAPI document; generate or inspect it only in a trusted development/staging environment. JSON
requests use strict schemas and bounded pagination. Authentication uses short-lived Bearer access
tokens plus a rotating opaque HttpOnly refresh cookie scoped to auth routes.

Primary resource groups are `auth`, `workspaces`, `conversations`, `commands`, `plans`, `tasks`,
`projects`, `approvals`, `crm`, `marketing`, `automations`, `knowledge`, `integrations`,
`notifications`, `analytics`, `subscriptions`, and `data-portability`. Mutating operations return
validated representations or accepted/job state; errors use stable HTTP semantics without stack
traces. Tenant-owned IDs are always resolved through active membership.

Clients must send `Content-Type: application/json`, handle `401` by performing one refresh attempt,
respect `403/404` boundaries, and never retry non-idempotent external writes without the operation's
idempotency contract. Propagate `X-Request-ID` for support correlation. `/health` is liveness,
`/ready` checks PostgreSQL/Redis, and `/metrics` is bearer-protected in production.

The authoritative route/schema contract lives in `apps/api/app/api` and generated OpenAPI. Any API
change requires compatibility review, tests, and an explicit migration when persistence changes.
