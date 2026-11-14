# Investor demo — 12 minutes

Use only the workspace `sporting-cp-demo`, visibly labelled **Synthetic demo workspace**. All people,
addresses, pipeline values, campaigns, knowledge, and activity are fictional. Provider domains use
`.invalid`; integrations remain disabled; nothing is emailed, published, billed, or pushed.

## Script

1. **0:00–1:30 — Problem and workspace.** Show the public proposition, sign in as the synthetic
   Owner, and point out tenant identity, role, plan, and demo warning.
2. **1:30–4:00 — Ask Kiko.** Request a fictional membership-retention campaign. Show the persistent
   conversation, command provenance, Supervisor plan, specialist assignment, and grounded knowledge.
3. **4:00–6:00 — Governed execution.** Open Tasks/Kanban, dependencies and history. Show that a risky
   action stops at Approval and cannot be self-approved by its requester.
4. **6:00–8:00 — Business context.** Open the synthetic Client 360, opportunity/project/activity and
   the draft marketing campaign. Explicitly state that drafts are not provider publication.
5. **8:00–10:00 — Control.** Show Agent Center health, integration reconciliation, notifications,
   analytics/activity, workspace roles, entitlements, auditability, export and retention preview.
6. **10:00–12:00 — Trust and close.** Demonstrate the outsider isolation check, mobile layout, and
   explain approval, idempotency, encrypted credentials, backup/restore, and staged activation.

## Rehearsal

Seed idempotently with `python -m app.scripts.seed_sporting_demo_knowledge`. Reset only an already
flagged synthetic workspace using `--reset --confirm-synthetic-reset sporting-cp-demo`. A reset of a
real workspace or a mismatched slug must fail. Before presenting, run the critical E2E suite, confirm
the banner, walk the timed script, and keep a screenshot-only fallback. Never improvise real claims.
