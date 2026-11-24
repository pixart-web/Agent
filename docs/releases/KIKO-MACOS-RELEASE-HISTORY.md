# Kiko for macOS — release history

Internal, unsigned release candidates (ad-hoc signature, hardened runtime; not Developer ID
signed, not notarised). Requires an Apple Silicon Mac with macOS 12+; 32 GB is recommended when
the AI model runs on the same Mac. The current release has its own notes
(`KIKO-MACOS-<version>-RELEASE-NOTES.md`); earlier versions are summarised here.

| Version | Date       | Highlights                                                                                                                                                                                                                             | DMG SHA-256                                                        |
| ------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| 0.3.3   | 2026-11-23 | Abandoned AI runs fail within ~30 s (KQA-030); model work on its own queue; Kiko styles for older buttons (KQA-029); named logo link (KQA-028); one request fewer after a reload                                                       | `64b56e3bfd3ada4d109d8426665db882f5c164384818a6eac4ffccb6a10fb801` |
| 0.3.2   | 2026-11-23 | Animated Kiko redrawn after the official logo; all ten live states kept                                                                                                                                                                | `5b9b9b8a89704e6e5cc22ce3edc2f2bbdbd2496cb892a07ee105fc20e2d2a0a7` |
| 0.3.1   | 2026-11-23 | Official Kiko logo on sign-in/account screens and navigation; app icon and favicon from the logo's robot                                                                                                                               | `68edbb299022036dfd987b04252603e66118372596863effbedabd71c2afeae4` |
| 0.3.0   | 2026-11-21 | Kiko Alive: dark identity, live Kiko character, navigation rail with ⌘K and workspace switcher, new home with the request box, stage headers on work screens, "Terminar sessão"                                                        | `48c52497b0aea38f9283c976d64d971abe6e8b23669262aaf4fc9985fe79b31e` |
| 0.2.3   | 2026-11-20 | Specialist agents run in the background with progress; recovery advice when the local AI is unavailable; interrupted agent runs no longer block a task                                                                                 | `35652219c106ee639e0b2b842c0d94debefed9132f3dff1f699093b8c7d2f511` |
| 0.2.2   | 2026-11-20 | Supervisor plans in the background with progress; controls follow the role; read-only "Join <company>" onboarding for invitees; interrupted plans no longer block a command                                                            | `9d8f13342d3161bee22755ddf0d53ec2a804bc85e55ef52403e2229d5afacc50` |
| 0.2.1   | 2026-11-20 | Fixed: page suspended behind other windows (macOS 27.2.1); invitees stuck on company setup; viewers able to write. Faster CRM contact list                                                                                             | `0a73c051603bc82500679d62f8957549ae16422817e8ec000b7906dcf6345935` |
| 0.2.0   | 2026-11-15 | Local AI only (Ollama, `gemma4:12b-it-qat`); valid specialist tool proposals with local models; notification freeze and cold-start deep links fixed; resilient background dispatchers; accessibility fixes; Codex integration disabled | `c418fac1416a4a67922608400b2b41e9b44d9862aa10a0d565c845f49b97aea3` |

Detailed evidence for every round is in `docs/qa/KIKO-FULL-QA-REPORT.md` and
`docs/qa/KIKO-FULL-DEFECT-REGISTER.md`; the redesign is documented in `docs/design/`.
