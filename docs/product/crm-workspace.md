# CRM workspace

The CRM workspace is the tenant-scoped source of truth for organizations, contacts,
clients, pipelines, opportunities, and linked business activity.

## Operator workflow

1. Create an organization and client, or add a contact to an existing organization.
2. Create a sales pipeline from the CRM page. The default template contains Lead,
   Qualified, Proposal, and Won stages.
3. Move opportunity cards with the stage selector. The server records each change in
   CRM history and the workspace audit log.
4. Open a client for the Client 360 view: contacts, referenced emails and meetings,
   projects, tasks, opportunities, notes, activities, insights, and history remain
   visibly separated by provenance.
5. Archive or reactivate organizations, contacts, and clients from their detail pages.

Viewer memberships are read-only. Manual changes require an editor, admin, or owner
membership and are audited as user actions. Agent tool calls keep the existing action
governance and approval policy.

## CSV import and export

Imports accept UTF-8 CSV files up to 1 MB and 1,000 rows. Required columns are
`record_type` (`organization` or `contact`) and `name`. Optional columns are
`website`, `organization_name`, `email`, `phone`, and `tags`.

The preview endpoint validates every row and returns a SHA-256 fingerprint. Confirmation
is rejected if the file changed, if a row is invalid, or if an organization is duplicated.
The operation therefore never silently imports a different file from the one reviewed.

CSV and JSON exports are tenant scoped. CSV cells beginning with spreadsheet formula
characters are escaped. The current bounded export contains at most 100 records per
resource; larger workspaces should use the paginated API until an asynchronous export
job is introduced.

## API surface

- `POST/PATCH /api/v1/crm/organizations`
- `POST/PATCH /api/v1/crm/contacts`
- `POST/PATCH /api/v1/crm/clients`
- `POST /api/v1/crm/pipelines`
- `POST/PATCH /api/v1/crm/opportunities`
- `POST /api/v1/crm/import/preview`
- `POST /api/v1/crm/import/confirm`
- `GET /api/v1/crm/export`

Duplicate organizations and clients return HTTP 409. Invalid input returns HTTP 422;
missing tenant resources return HTTP 404 without revealing cross-workspace existence.
