# Authorized Google integration validation

This release has deterministic fake-provider coverage for OAuth, reads, governed writes,
idempotency, failure mapping, and ambiguous delivery. A production-readiness claim additionally
requires an operator to validate both APIs with dedicated, authorized, allowlisted test accounts.

## Evidence checklist

- Record the UTC date, release commit, operator, Google test account, and consent-screen mode.
- Run the Gmail read-only smoke and verify profile plus a bounded message read.
- With explicit authorization, send only to the nominated test recipient and record the message
  identifier. Verify it once in Gmail; never retry an ambiguous result automatically.
- Run the Calendar read-only smoke and verify primary calendar plus bounded event listing.
- With explicit authorization, create the named smoke event, verify it once in Calendar, record
  the event identifier, and remove it manually.
- Expire or revoke each test credential and verify the dashboard becomes `degraded`.
- Simulate or observe an ambiguous provider write and verify `reconciliation_required`, the
  unresolved counter, and the no-retry warning.
- Disconnect the accounts and confirm encrypted credentials are destroyed.

Do not paste refresh tokens, OAuth secrets, encryption keys, message bodies, or calendar content
into the evidence document. Store the completed evidence in the release system, not in Git.

## Current environment

On 2026-10-12 the local release workspace had no Google client credentials, integration key,
allowlists, or smoke refresh tokens configured. Real-provider validation therefore remains an
external release-gate item; it has not been represented as passing.
