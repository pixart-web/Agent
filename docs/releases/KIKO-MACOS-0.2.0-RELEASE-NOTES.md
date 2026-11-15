# Kiko for macOS 0.2.0 — release candidate notes

**Status:** release candidate for **owner acceptance testing** (internal, unsigned).
**Built:** 2026-11-15 from `cf645d04b16aa4f3d1c5a58cf45b70df29dbf4c9` (clean tree), branch
`qa/kiko-full-system-hardening`. Evidence: `docs/qa/KIKO-FULL-QA-REPORT.md`.

## What's new since 0.1.0

- **Local AI only.** Supervisor plans, Kiko AI, specialist agents and summarisation run on a local
  model (Ollama, `gemma4:12b-it-qat`); no external AI service is contacted. The app waits up to
  10 minutes for AI generation (local generation takes about 35–65 s on an M4).
- Specialist agents now produce valid tool proposals with local models.
- Fixed: freeze after native notifications; `kiko://` links when the app is closed (both from
  PR #33); background email/execution dispatchers survive database restarts; accessibility fixes
  on several dashboard screens; Next.js security update for the web edition.
- Codex development integration is disabled (it relied on an external AI service).

## Artifact

|          |                                                                                        |
| -------- | -------------------------------------------------------------------------------------- |
| File     | `Kiko_0.2.0_aarch64.dmg` (5,308,934 bytes)                                             |
| SHA-256  | `c418fac1416a4a67922608400b2b41e9b44d9862aa10a0d565c845f49b97aea3`                     |
| Requires | Apple Silicon Mac, macOS 12+; 32 GB recommended when the AI model runs on the same Mac |
| Signing  | ad-hoc (hardened runtime); **not** Developer ID signed, **not** notarised              |

## Installation (internal testing)

1. Start the backend: `scripts/local/kiko-local.sh start` (and make sure Ollama is running with
   `gemma4:12b-it-qat`).
2. Open the DMG and drag **Kiko** to **Applications**. This replaces 0.1.0; the stored server
   address and Keychain session are kept.
3. First launch: **right-click Kiko → Open → Open** (Gatekeeper; the build is not notarised).
4. **Kiko → Server Connection…** → `http://localhost:8000` (plain HTTP is accepted only for
   loopback addresses).
5. Emails (verification, password reset) arrive in Mailpit at http://127.0.0.1:58025.

## Deployment readiness checklist

| Item                                            | Status                                                                                            |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| All required CI checks pass                     | ✅ (Backend, Frontend, PostgreSQL+Redis incl. full suite, container build; Desktop job on the PR) |
| Critical user journeys pass                     | ✅ smoke 20/20, desktop journey with local AI, workflows B/H/L/F                                  |
| No open BLOCKER/CRITICAL/HIGH security findings | ✅                                                                                                |
| Database migrations validated                   | ✅ upgrade/downgrade/re-upgrade; ⚠️ model drift KQA-010 (LOW)                                     |
| Multi-tenant isolation verified                 | ✅ IDOR sweep 93 operations, 0 leaks                                                              |
| Authentication and authorisation                | ✅                                                                                                |
| Native macOS behaviour tested                   | ✅ journey + release build; ⚠️ menus/palette/save panel not automated                             |
| Persistence and recovery tested                 | ✅ service restarts, PostgreSQL outage, AI runtime outage                                         |
| Real AI validated                               | ✅ local model, 25/25 checks, loopback-only egress                                                |
| External integrations                           | ⚠️ Gmail/Calendar/GitHub disabled (credentials); Codex excluded                                   |
| Operational requirements documented             | ✅ QA report §23, `docs/ai/KIKO-LOCAL-AI-MIGRATION.md`                                            |
| Remaining limitations accepted                  | ⏳ owner decision                                                                                 |
| Deployment configuration reviewed               | ⚠️ production config validated in code; inference host not chosen                                 |
| Rollback and backup procedures                  | ✅ `docs/production-readiness.md`; AI degrades to 503 without the runtime                         |
| Signed + notarised build                        | ❌ needs Apple Developer ID                                                                       |
| HTTPS staging backend                           | ❌ needs owner                                                                                    |
| Production inference host                       | ❌ needs owner decision (Hetzner not assessed or modified)                                        |
