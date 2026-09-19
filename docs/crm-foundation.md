# CRM foundation

Phase 5D introduces a user-scoped, workspace-ready business identity domain. It includes
organizations, contacts, multiple contact methods, organization memberships, structured
addresses, tags, notes and activities. Every aggregate carries explicit ownership; Phase 9 can
add workspace ownership through a migration without weakening current user isolation.

## Identity rules

Names are Unicode-normalized for search but are never unique and never trigger automatic
merges. Emails are lower-cased and phones are reduced to a stable international-style identity,
but identical methods may still belong to more than one contact. Ambiguous exact matches return
all owned candidates and require a human decision.

## Governance

CRM reads are green. Create organization/contact, update contact, add note and link Email or
Calendar references are yellow, approval-gated and fingerprinted. Create operations store the
originating TaskAction as an idempotency key. Updates are exact-payload and transactionally
repeat-safe. Approval previews show the complete mutation payload.

Email and Calendar associations use `EmailReference` and `CalendarReference`; mailbox bodies and
event descriptions are not copied into CRM. Reference ownership is verified through the
provider account before a link is created. Activities retain provider identifiers and minimal
metadata only. CRM notes and external reference metadata remain untrusted content for agents.

## Demo data

Tests use only synthetic records such as `Sporting CP Demo` and `João Sponsor Demo` with reserved
`.example` addresses. No Sporting system is contacted and no real customer relationship is
implied.

Migration `20260919_0011` follows Calendar head `20260919_0010` and has a full downgrade.
