# Automation tenant inheritance

`automations.workspace_id` is the canonical tenant root. Automation runs retain
`user_id` as the initiating actor, but authorization and history listing join every
run back to its Automation and compare that root with the caller's active workspace.

Migration `20261010_0024` replaces the obsolete actor-oriented run-history index with
`(automation_id, created_at)`, matching workspace history queries through the root.
The run table does not duplicate `workspace_id`, avoiding divergent tenant values.

Email and Calendar trigger configuration validates integration accounts against the
same active workspace. Email and Calendar reference records likewise inherit tenant
identity from `integration_accounts`; their optional task and command links point to
the already workspace-scoped execution graph.

An adversarial test proves that a second member can inspect run history in the shared
workspace while a user whose active workspace is isolated receives an empty result.
