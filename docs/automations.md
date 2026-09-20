# Governed automations

Phase 8 adds durable, user-owned automations without creating a second execution path.

```text
Typed trigger -> declarative conditions -> guardrails -> Command
              -> transactional outbox -> Celery -> Supervisor
              -> draft Plan -> human plan approval -> agents
              -> TaskAction risk/fingerprint -> action approval -> tool
```

An automation can create and submit a command for planning. It cannot approve a plan, approve
an action, lower effective risk, select credentials, invoke a tool, or publish/send externally.
The existing Supervisor, agent allowlists, Execution Engine and exact-payload approval flow remain
the only route to side effects.

## Trigger contract

Supported trigger types are `schedule`, `email_received`, `calendar_event`, `crm_change`,
`task_state`, `manual`, and `webhook`. Trigger configuration is allowlisted per type; there is no
arbitrary code, expression language, URL callback, shell, or dynamic import. Conditions support
only bounded nested-field `eq`, `not_eq`, `in`, and `exists` comparisons.

Email, Calendar, CRM and task adapters call `AutomationService.dispatch_event` after their own
owned event is committed. Public arbitrary event ingestion is intentionally absent. Manual and
webhook automations may be triggered only through the authenticated owner API in this phase.
A future public webhook adapter must authenticate its source and translate the event into this
same service contract.

Event payloads are capped at 32 KiB, sanitized for secret-like fields and stored only on the run.
They are untrusted data and are never interpolated into the static command sent to the Supervisor.
This prevents an email body, calendar description, CRM note or webhook value from becoming an
instruction.

## Loop and cost protection

Each automation has:

- a unique SHA-256 deduplication key derived from automation, trigger type and provider event key;
- a database unique constraint and row lock so duplicate/concurrent delivery creates one command;
- an explicit causation run and bounded depth (maximum configurable value 10);
- a per-window execution budget;
- a cooldown;
- conditions evaluated before command creation;
- an auditable skipped run for condition, depth, budget and cooldown rejections.

Redis is not authoritative for these controls. PostgreSQL stores automations, runs, dedupe keys,
correlation/causation, commands and audit records.

## Schedules and recovery

Run due schedules explicitly with:

```bash
python -m app.scripts.run_due_automations
```

The runner advances the next due time while holding the automation lock. Multiple schedulers may
observe the same due item, but the persistent dedupe key allows only one command. Scheduling this
script is an operations concern; no production scheduler is configured by this phase.

Failed runs require an authenticated manual recovery request. Recovery creates one causally linked,
deduplicated child run and is still subject to depth, cooldown and budget controls. There is no
unbounded automatic retry.

## API and UI

Authenticated endpoints under `/api/v1/automations` support create/list/detail, pause, resume,
manual or authenticated-webhook trigger, run history and failed-run recovery. The dashboard at
`/dashboard/automations` shows configuration, guardrail outcomes, correlation IDs and generated
commands. Event payloads are not returned by the API or rendered in the UI.

## Sporting Demo

A synthetic `calendar_event` automation can react to a demo matchday checkpoint and create the
static command `Prepare the governed Sporting Demo matchday plan.` The Supervisor may propose
Marketing, Operations and Support work, but every external Email, Calendar, GitHub or other write
still pauses at its existing approval gate. No real Sporting system or account is contacted.
