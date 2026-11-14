# Kiko commercial release candidate — release notes

Date: 2026-10-14. This candidate completes the repository roadmap R0–R8 and stops before staging or
production deployment.

Highlights include complete identity recovery/session/profile flows; canonical workspaces, roles,
invitations and onboarding; persistent Kiko conversations; lifecycle-complete commands, projects,
tasks and approvals; CRM, Marketing, Automations and safe Knowledge ingestion; governed provider
configuration and reconciliation; notifications, analytics, activity, team/platform/settings and
data portability; commercial plans and entitlements; and the public product site.

Release hardening adds a production CSP/security-header policy, disabled production OpenAPI,
secret-safe provider configuration, remediated dependency advisories, PostgreSQL/Redis concurrency
and tenant tests, browser E2E on desktop/mobile, WCAG 2 A/AA automated checks, bounded load evidence,
backup/restore rehearsal, clean migration 0035, production container builds, and an explicitly
flagged synthetic demo workspace.

Database migrations are linear through `20261014_0035`. Apply them through the single migration job
before application traffic. Review the readiness report and known limitations before any deployment.
