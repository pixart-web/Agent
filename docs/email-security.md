# Email security

Email is an untrusted integration boundary. The LLM and specialist agents never receive
Google client secrets, refresh/access tokens, an HTTP client, raw MIME, or a way to select
arbitrary OAuth scopes.

## Credential boundary

Google authorization code exchange and refresh happen in backend code. Only the refresh
token is retained and it is encrypted with Fernet using INTEGRATION_ENCRYPTION_KEY.
The key is supplied by the runtime, is not stored in PostgreSQL, and must be managed
separately from database and authentication credentials. Access tokens are short-lived
and memory-only. Disconnect revokes the credential when possible and overwrites the stored
ciphertext with a revoked marker.

Secrets are excluded from tool schemas, TaskAction, TaskExecution, API responses, frontend
state, approval descriptions, logs, and audit metadata. Production credentials must never
be committed.

## Content boundary

Message content, senders, links, quoted text, signatures, and attachments are external data,
not instructions. Outputs carry external_content=true and trust=untrusted. Plain text is
preferred. HTML is parsed into inert text and never rendered directly. Attachment content
is not fetched; only bounded metadata is returned. Executable extensions and oversized
attachments are marked blocked.

These controls reduce prompt-injection risk but do not claim perfect detection. The
DataClassificationPolicy hook permits future DLP/classification checks without granting
the model access to secrets or provider APIs.

## Side effects

List, get, thread, and search are green reads. Send, reply, and mark-read are yellow and
require a fingerprint-matching human approval. Recipient count and message size are bounded.
Only allowlisted mailbox accounts can connect.

EmailSendRecord reserves an approved action before the provider call. Successful repeats
return the recorded result. Any payload mismatch fails. Write timeouts or ambiguous provider
responses become delivery_unknown and are never retried automatically. Definite failures
are terminal for that action; a new attempt requires a new reviewed action.

Audit records use account/provider identifiers and bounded counts only. Message bodies,
arbitrary headers, client secrets, and tokens are never audit metadata.
