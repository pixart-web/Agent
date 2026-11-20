# Kiko for macOS 0.3.0 — release candidate notes

**Status:** release candidate for **owner review** before the comprehensive QA program
(internal, unsigned). **Built:** 2026-11-20, branch `feature/kiko-alive-ui`.

## Changes since 0.2.3 — Kiko Alive

- New dark visual identity across the app.
- Kiko the character: shows what the workspace is really doing (available, listening,
  thinking, planning, executing, waiting for approval, done, needs attention, offline,
  resting).
- New navigation rail (collapsible) with every module, ⌘K search, workspace switcher and an
  activity panel (approvals, executions in progress, agents, recent activity).
- New home: "O que queres que eu faça hoje?" starts a conversation with the local AI; quick
  actions; real progress, agents and integrations.
- Commands, conversations and reports show which stage the work is in.
- Logout is now "Terminar sessão" at the bottom of the navigation.

Details: `docs/design/KIKO-ALIVE-IMPLEMENTATION-REPORT.md`.

## Artifact

|          |                                                                                        |
| -------- | -------------------------------------------------------------------------------------- |
| File     | `Kiko_0.3.0_aarch64.dmg` (5,588,999 bytes)                                             |
| SHA-256  | `ba7185ed6481ba1ce4abdf8642c71576ce07cb0cc23d243ff1e370453395c362`                     |
| Requires | Apple Silicon Mac, macOS 12+; 32 GB recommended when the AI model runs on the same Mac |
| Signing  | ad-hoc (hardened runtime); **not** Developer ID signed, **not** notarised              |
