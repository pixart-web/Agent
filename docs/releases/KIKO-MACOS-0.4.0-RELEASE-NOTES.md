# Kiko for macOS 0.4.0 — release candidate notes

**Status:** release candidate for **owner review** (internal, unsigned).
**Built:** 2026-11-28, branch `release/kiko-0.4.0` (main at `b64af9e`).

## Changes since 0.3.7

- **Two-factor authentication.** Any account can turn on verification in two steps in
  Definições, with an authenticator app (QR code or manual key) and ten single-use recovery
  codes. Sign-in then asks for the code ("Confirma que és tu"); the macOS app keeps the
  session in the Keychain as before.
- **Execution flow.** The command workspace shows "Dependências e passos": the plan's tasks by
  dependency stage and, for each task, a log of status changes, agent runs and tool attempts.
- **New public page** in Portuguese with the Kiko identity (logo, animated Kiko, midnight and
  amber); the onboarding cards show the Kiko logo.
- **Cold-start measurement.** Each launch records, on this Mac only, how long the window, the
  first page and the first usable screen took (`~/Library/Logs/pt.pixart.kiko/startup.jsonl`).
- **Pixart products registry.** Platform admins can register Pixart products; they appear in
  Integrações as "Sem contrato verificado" until their API contract is recorded. No product
  is connected yet.
- Measured on this Mac (5 cold starts of the installed app, signed out): window 163 ms,
  first page 253 ms, first usable screen 294 ms (median; p95 380 ms).
- The desktop test journey now also covers Marketing, Automations, Knowledge, two-factor
  sign-in and password reset (9 app launches, all green).

## Artifact

|          |                                                                                        |
| -------- | -------------------------------------------------------------------------------------- |
| File     | `Kiko_0.4.0_aarch64.dmg` (5,268,516 bytes)                                             |
| SHA-256  | `935316a7915a677b38bfbfc18d5909ce8dcdea92269c16fca2a414ee8c8414a7`                     |
| Requires | Apple Silicon Mac, macOS 12+; 32 GB recommended when the AI model runs on the same Mac |
| Signing  | ad-hoc (hardened runtime); **not** Developer ID signed, **not** notarised              |
