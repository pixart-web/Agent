# Kiko for macOS 0.3.3 — release candidate notes

**Status:** release candidate for **owner review** (internal, unsigned).
**Built:** 2026-11-23, branch `fix/kiko-deep-test-round2`.

## Changes since 0.3.2

- Plans and agent runs abandoned by a stopped server no longer show "working…" forever; they
  are marked failed within about 30 seconds (KQA-030).
- Model work runs on its own queue, one at a time: several plans or agents at once wait their
  turn instead of timing out, and approved actions never wait for the AI.
- Buttons in the older screens (automations, knowledge, tasks, marketing) use the Kiko style
  (KQA-029); the Kiko logo link has a name for screen readers on phones (KQA-028).
- Pages load one request faster after a reload (the session is renewed before the first call).

## Artifact

|          |                                                                                        |
| -------- | -------------------------------------------------------------------------------------- |
| File     | `Kiko_0.3.3_aarch64.dmg` (6,946,719 bytes)                                             |
| SHA-256  | `64b56e3bfd3ada4d109d8426665db882f5c164384818a6eac4ffccb6a10fb801`                     |
| Requires | Apple Silicon Mac, macOS 12+; 32 GB recommended when the AI model runs on the same Mac |
| Signing  | ad-hoc (hardened runtime); **not** Developer ID signed, **not** notarised              |
