# Isolated staging and test accounts

## Environment contract

Provision an isolated hostname, PostgreSQL database, Redis namespace, object storage prefix, secret
set, encryption keys, OAuth applications, queues, and observability labels. Staging must not share
production credentials or data. Build the exact release SHA into immutable API and Web images and
pin their digests in the release manifest. Route API paths same-origin through TLS.

Apply migrations once, seed the agent catalogue, then create two dedicated accounts through the
normal product flow:

- `owner-staging@<controlled-domain>`: Workspace Owner for the synthetic demo;
- `outsider-staging@<controlled-domain>`: Owner of a separate workspace for isolation tests.

Use addresses controlled by the release team, unique passwords from the password manager, MFA when
available, and no employee/customer data. The outsider must receive `404` for the first workspace's
CRM object and `403/404` for its invitations. Revoke sessions and rotate credentials after a demo.

## Gate sequence

1. Verify manifest SHA/digests, configuration validation, dependency and image scans.
2. Restore the latest staging backup into a new database and verify checksum/migration head.
3. Deploy with all external integrations disabled; check health, readiness, logs, metrics, and queues.
4. Complete registration, verification, login, onboarding, command, plan, approval, task, export, and
   tenant-isolation journeys on desktop and mobile.
5. Enable each authorized test provider separately, verify minimum scopes and reconciliation, then
   disable it again if production enablement is not approved.
6. Run bounded load and accessibility gates, rehearse rollback, archive evidence, and record go/no-go.

No step authorizes a production deployment or real customer/external write.
