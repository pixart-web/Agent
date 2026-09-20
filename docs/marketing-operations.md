# Governed marketing and content operations

Phase 7 adds an owned campaign and content workflow for Kiko. It is deliberately an internal
planning system, not a social-network publishing client.

## Domain and lifecycle

Campaigns may reference an owned CRM client and contain content items optionally linked to an
owned Kiko task. Content follows an explicit lifecycle:

idea → draft → review → approved → scheduled → published → archived

Only allowed transitions are accepted. Content can be edited only in idea or draft. A reviewed
item may return to draft; scheduling requires approved content and a future timestamp.
Published is never produced by an outbound API call. The approval-gated
marketing.record_publication tool stores an independently confirmed external reference and
timestamp after the fact.

Assets store metadata and a locator only; no binary upload or remote fetch is performed.
Performance records store attributed metric metadata and never trigger external collection.

## Governance

Marketing reads are GREEN. Campaign/content mutations, transitions, schedules, asset metadata,
publication confirmations and performance metrics are YELLOW, exact-payload approved,
fingerprinted, audited and non-retrying. Every query and relationship is scoped to user_id.
Referenced CRM clients and Kiko tasks are revalidated through their ownership chain.

Campaign objectives, draft copy, asset locators/metadata and performance metadata are untrusted
business content. Agent prompts forbid treating them as instructions. The UI renders them as
text and labels publication records as externally confirmed.

There is intentionally no marketing.publish tool, provider SDK or network adapter. Synthetic
Sporting Demo tests use only reserved/demo values and publish nothing.

Migration 20260919_0013 follows head 20260919_0012 and supports full downgrade.
