# Kiko for macOS 0.3.6 — release candidate notes

**Status:** release candidate for **owner review** (internal, unsigned).
**Built:** 2026-11-25, branch `release/kiko-0.3.6` (main at `c65b09f`).

## Changes since 0.3.5

- Error and validation messages from the server are shown in European Portuguese: workflow
  rules ("A tarefa não pode passar de pronta para concluída."), duplicates, permissions,
  missing records, local AI problems and form validation, naming the field concerned.
- When an operation fails, the screen's own message is followed by the server's reason, e.g.
  "Não foi possível concluir a operação da automatização. Já existe uma automatização com este
  nome."
- Errors stored on agent runs, executions, commands and Codex runs are shown in Portuguese.
- Automation cards in Portuguese: "Ativa" / "Em pausa", the chaining and execution limits, and
  the reason a safety limit skipped a run.

Still in English: messages from internal tooling (backups, the Codex runner, the outbox) that
are not shown on Kiko's screens, and server logs.

## Artifact

|          |                                                                                        |
| -------- | -------------------------------------------------------------------------------------- |
| File     | `Kiko_0.3.6_aarch64.dmg` (7,378,145 bytes)                                             |
| SHA-256  | `f23723b46dd5756f03af845c1e84d98d568c3380fc1eb9b3b1ca49584fb440af`                     |
| Requires | Apple Silicon Mac, macOS 12+; 32 GB recommended when the AI model runs on the same Mac |
| Signing  | ad-hoc (hardened runtime); **not** Developer ID signed, **not** notarised              |
