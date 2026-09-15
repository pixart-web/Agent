# Email integration

Phase 5B adds provider-neutral email through EmailTool -> EmailService ->
EmailProvider -> GmailProvider. Gmail is the first provider; agents never receive OAuth
tokens, provider clients, raw MIME, or arbitrary headers.

## Setup

Create a Google OAuth 2.0 Web application and register GOOGLE_REDIRECT_URI exactly as
configured, normally http://localhost:8000/api/v1/integrations/email/callback. Enable the
Gmail API. Set a Fernet key generated with Fernet.generate_key() as
INTEGRATION_ENCRYPTION_KEY; do not reuse the database password or authentication secret.

Keep EMAIL_INTEGRATION_ENABLED=false and EMAIL_SEND_ENABLED=false until an operator has
reviewed the allowed accounts and Google consent-screen configuration. No real Google
credential is required by CI.

OAuth requests use authorization code flow, signed short-lived state, offline access, and
minimum scopes:

- gmail.readonly for list, search, message, and thread reads;
- gmail.send only when sending is enabled;
- gmail.modify only when mark-read is enabled.

Only the encrypted refresh token is persisted. Access tokens are refreshed in backend
execution and never stored in actions, executions, API responses, the dashboard, or audit
metadata. Disconnect revokes the token where possible and destroys the stored credential.

## Governance

Read tools are green: email.list_messages, email.get_message, email.get_thread, and
email.search. email.send, email.reply, and email.mark_read are yellow and always require
human approval. The approval description contains the account, full recipients, subject,
complete body, and risk warning. Its fingerprint covers the exact action payload.

Support v2 can read, search, reply, and mark read. Sales v2 can read, search, send, and
reply. Marketing and Development have no email tools. Sending is disabled by default,
recipient count is bounded, and only allowlisted mailbox accounts can connect.

Email bodies are untrusted data. Plain text is preferred; HTML is converted to inert text
and is never rendered as arbitrary HTML. Attachments return metadata only. Executable
extensions and oversized attachments are marked blocked; Kiko never downloads or executes
them automatically. DataClassificationPolicy is an extension point for DLP rather than a
claim of perfect sensitive-data detection.

## Delivery and retries

Reads are on demand and no mailbox is replicated. Transient read failures and rate limits
may retry within the tool budget. Writes have zero automatic retries. A write timeout or
ambiguous provider response records delivery_unknown; an operator must investigate before
creating a new approved action. EmailSendRecord makes successful actions idempotent and
rejects payload changes after approval.

Audit events contain provider/account identifiers and bounded counts, never message bodies,
tokens, client secrets, or arbitrary headers.

## Operations

Safe UI pages are /dashboard/integrations/email, /dashboard/email, and
/dashboard/email/[message_id]. Analyze with Kiko and Prepare reply create workflow commands
only; neither sends directly.

Run the read-only smoke test from apps/api with EMAIL_SMOKE_REFRESH_TOKEN set:

    python -m app.scripts.test_email_integration

The send path additionally requires EMAIL_SEND_ENABLED=true, an explicit operator flag and
recipient:

    python -m app.scripts.test_email_integration --allow-send --recipient operator@example.com
