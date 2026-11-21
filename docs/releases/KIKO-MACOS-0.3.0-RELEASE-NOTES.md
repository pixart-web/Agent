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
- Sign-in and account screens show the Kiko logo; "Sign in to Kiko", "PIXART Ecosystem".
- New app icon: Kiko on a midnight tile with the amber halo (also the web favicon).

Details: `docs/design/KIKO-ALIVE-IMPLEMENTATION-REPORT.md`.

## Artifact

|          |                                                                                        |
| -------- | -------------------------------------------------------------------------------------- |
| File     | `Kiko_0.3.0_aarch64.dmg` (6,253,720 bytes)                                             |
| SHA-256  | `48c52497b0aea38f9283c976d64d971abe6e8b23669262aaf4fc9985fe79b31e`                     |
| Requires | Apple Silicon Mac, macOS 12+; 32 GB recommended when the AI model runs on the same Mac |
| Signing  | ad-hoc (hardened runtime); **not** Developer ID signed, **not** notarised              |
