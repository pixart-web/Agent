# Kiko conversations

Kiko AI provides a workspace-scoped conversational entry point for operational work.

## Persistence and execution contract

- Conversations belong to the active workspace and are visible to members of that workspace.
- Every user message is stored and creates one real `Command` in the same database transaction.
- The command retains its `conversation_id`, so planning, execution, approvals, audit history, and cancellation continue through the existing governed workflow.
- Kiko's persisted acknowledgement links to the command; it does not claim that work has already succeeded.
- Reloading or returning later restores the conversation and all command links.

## API

- `POST /api/v1/conversations` starts a conversation with its first operational message.
- `GET /api/v1/conversations` lists active conversations in the current workspace.
- `GET /api/v1/conversations/{id}` returns the persisted thread.
- `POST /api/v1/conversations/{id}/messages` appends a message and creates its command.

All object access is scoped server-side to the authenticated user's active workspace. Cross-workspace identifiers return `404`.

## Current boundary

This increment establishes durable threads and governed command creation. Generated plan summaries, execution results, approval prompts, and failure/reconciliation events are still viewed in the linked command workflow. Projecting those lifecycle events back into the conversation is the next R2 increment.
