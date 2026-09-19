# Operational client management

Phase 6 extends the CRM identity foundation into governed client operations without becoming a
generic CRM clone. A client profile is anchored to one owned CRM organization and adds an
explicit owner, lifecycle status, industry and concise business summary.

## Domain

- CrmClient turns an owned organization into an operational client.
- CrmProject tracks client work with an owner, lifecycle and dates.
- CrmPipeline and ordered CrmPipelineStage records define an owned commercial process.
- CrmOpportunity links a client, optional owned contact, pipeline/stage, value, probability,
  status and expected close date.
- CrmTaskLink associates an already owned Kiko task with a client and optional client project.
- CrmRecordHistory stores append-only, action-attributed mutation history.

Existing CRM contacts, memberships, notes and activities remain the source of relationship
identity. Email and Calendar continue to be linked by minimal owned references; mailbox and
event bodies are not copied.

## Client 360

The crm.get_client_360 tool and GET /api/v1/crm/clients/{id}/360 aggregate only records owned by
the authenticated user:

- organization overview and contacts;
- linked email and meeting reference activities;
- projects and linked Kiko tasks;
- opportunities;
- notes, activities and mutation history;
- Kiko insights with explicit provenance.

Database-derived insights use kind=fact and provenance=system_fact. A future model-generated
summary must use kind=model_summary and provenance=llm. The UI renders these labels prominently
and never presents generated text as a verified CRM fact.

## Governance

Client-management reads are GREEN. Client, project, pipeline, opportunity and task-link
mutations are YELLOW, require exact-payload approval, have no automatic retry and write both an
audit event and CRM record history. Sales owns commercial mutations; Support can update projects
and link owned tasks; Marketing, Sales and Support may read Client 360 context.

Every service query carries the current user_id. Related organizations, contacts, pipelines,
stages, projects and tasks are revalidated as owned before use. Cross-client contact links and
cross-client project links are rejected. External CRM notes and provider metadata remain
untrusted content for every agent.

Migration 20260919_0012 follows CRM foundation head 20260919_0011 and has a full downgrade.
