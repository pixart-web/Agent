# Kiko for macOS 0.2.3 — release candidate notes

**Status:** release candidate for **owner acceptance testing** (internal, unsigned).
**Built:** 2026-11-20, branch `feat/kiko-background-agents`.

## Changes since 0.2.2

- **Specialist agents work in the background.** "Ask agent to prepare actions" answers at
  once and shows the elapsed time; you can leave the page and the proposed actions are there
  when you come back. Running the agent again with feedback works the same way.
- **Clear advice when the local AI is not available.** Instead of only "Local AI runtime is
  not reachable", the app says what to do (start Ollama, install the model, try again, or
  contact the administrator).
- Fixed: an agent run interrupted by a stopped server no longer blocks the task.

## Artifact

|          |                                                                                        |
| -------- | -------------------------------------------------------------------------------------- |
| File     | `Kiko_0.2.3_aarch64.dmg`                                                               |
| SHA-256  | `35652219c106ee639e0b2b842c0d94debefed9132f3dff1f699093b8c7d2f511`                     |
| Requires | Apple Silicon Mac, macOS 12+; 32 GB recommended when the AI model runs on the same Mac |
| Signing  | ad-hoc (hardened runtime); **not** Developer ID signed, **not** notarised              |

Created with `hdiutil`. The backend must run the Celery worker for background plans and agent
runs (`scripts/local/kiko-local.sh start` does).
