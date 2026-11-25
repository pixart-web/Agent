# Kiko for macOS 0.3.5 — release candidate notes

**Status:** release candidate for **owner review** (internal, unsigned).
**Built:** 2026-11-25, branch `feat/kiko-pt-auth-server`.

## Changes since 0.3.4

- Sign-in, account (registration, password recovery, email verification, invitations),
  onboarding and the server-connection screens are in European Portuguese ("Entrar no Kiko").
- Authentication messages from the server are shown in Portuguese (wrong password, email not
  verified, too many attempts, expired links).
- Notifications, project activity and task history written by the server are in Portuguese,
  including entries stored in English before this version; native macOS notifications too.

Still in English: some detailed error messages from the server (validation and workflow rules).

## Artifact

|          |                                                                                        |
| -------- | -------------------------------------------------------------------------------------- |
| File     | `Kiko_0.3.5_aarch64.dmg` (6,957,291 bytes)                                             |
| SHA-256  | `9d493b94b2fe28da6d51a70d68cc3cdf6c1232ae6b0d5e7e65ff26dc761e6d65`                     |
| Requires | Apple Silicon Mac, macOS 12+; 32 GB recommended when the AI model runs on the same Mac |
| Signing  | ad-hoc (hardened runtime); **not** Developer ID signed, **not** notarised              |
