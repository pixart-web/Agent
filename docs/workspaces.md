# Workspace tenancy

Workspace is Kiko's company boundary. Membership is always checked server-side and
unknown or inaccessible workspace identifiers return the same not-found response.
The supported roles are `owner`, `admin`, `manager`, `member`, and `viewer`.

## Invitation lifecycle

Owners and admins can create and list invitations at
`/api/v1/workspaces/{workspace_id}/invitations`. Invitations:

- target a normalized email address;
- contain a random token whose SHA-256 hash is the only token representation stored;
- expire after `WORKSPACE_INVITATION_EXPIRE_HOURS`;
- are single-use and can be revoked before acceptance;
- invalidate an older pending invitation when resent;
- enforce one pending invitation per workspace and email in the database;
- create membership only when the authenticated, verified account email matches.

The raw token exists only in the encrypted transactional-email outbox. The email
links to `/invite`, where an authenticated recipient can accept it. Failed acceptance
does not reveal whether a workspace, invitation, or different target email exists.

Direct member insertion under the legacy Knowledge routes remains available for
backward compatibility. New product surfaces should use the invitation lifecycle.

## Remaining migration

Knowledge records are already workspace-scoped. Other business aggregates still
require staged `workspace_id` backfills before non-null constraints can be enforced.
Until those migrations land, their existing user ownership remains in force and must
not be represented as full tenant isolation.
