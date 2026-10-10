# Integration credential tenant migration

Integration credentials currently use `user_id` as both attribution and authorization.
They must move to Workspace ownership before Gmail, Calendar, or GitHub can be treated
as shared company capabilities.

## Staged rollout

1. Add nullable `workspace_id` to `integration_accounts` and backfill it from each
   owner's `active_workspace_id`.
2. Replace the uniqueness key with `(workspace_id, provider, external_account_id)` and
   make `workspace_id` non-null.
3. Resolve repository reads through the authenticated user's active membership while
   retaining `user_id` as the member who connected the account.
4. Persist the Workspace in OAuth state before redirect, so callback completion cannot
   attach credentials to a different Workspace if the user switches tabs meanwhile.
5. Restrict connect, reconnect, and disconnect to Owner/Admin; permit operational use
   according to module permissions.
6. Add adversarial tests for two workspaces, callback replay, mid-flow workspace switch,
   and an external account connected in more than one authorized tenant.

OAuth state scoping is mandatory: deriving Workspace only at callback time would create
a confused-deputy race and is not an acceptable implementation shortcut.
