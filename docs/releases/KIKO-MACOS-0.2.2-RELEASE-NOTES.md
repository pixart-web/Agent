# Kiko for macOS 0.2.2 — release candidate notes

**Status:** release candidate for **owner acceptance testing** (internal, unsigned).
**Built:** 2026-11-20 from `523b9cd` (clean tree), branch `feat/kiko-acceptance-improvements`.

## Changes since 0.2.1

- **Plans are prepared in the background.** "Gerar plano com Supervisor" answers at once; the
  page shows the elapsed time and you can leave it — the plan is there when you come back.
  Revising a plan with feedback works the same way.
- **Progress while the local AI works**, for plans and for specialist agent runs.
- **Controls follow your role.** Viewers no longer see forms and buttons they cannot use;
  members see workspace settings read-only; only the owner sees "Cancel at period end".
- **Invited members see "Join <company>"** with the company profile read-only, instead of the
  company setup form.
- Fixed: a planning run interrupted by a stopped server no longer blocks the command.

## Artifact

|          |                                                                                        |
| -------- | -------------------------------------------------------------------------------------- |
| File     | `Kiko_0.2.2_aarch64.dmg` (5,581,051 bytes)                                             |
| SHA-256  | `9d8f13342d3161bee22755ddf0d53ec2a804bc85e55ef52403e2229d5afacc50`                     |
| Requires | Apple Silicon Mac, macOS 12+; 32 GB recommended when the AI model runs on the same Mac |
| Signing  | ad-hoc (hardened runtime); **not** Developer ID signed, **not** notarised              |

Created with `hdiutil` (the bundler's Finder layout step times out on this Mac). The backend
must run the Celery worker for background planning (`scripts/local/kiko-local.sh start`
does).
