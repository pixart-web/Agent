# Kiko for macOS — release readiness

**Assessed:** 2026-11-14 · **Version:** 0.1.0 · **Branch:** `feat/kiko-macos-desktop`

## 1. Build classification

| Class                    | Status                                                                      |
| ------------------------ | --------------------------------------------------------------------------- |
| Local development build  | **Produced** — `Kiko_0.1.0_aarch64.dmg` (5.0 MB), ad-hoc signed             |
| Internal testing build   | Produced by CI as an unsigned artifact on every run (`Desktop (macOS)` job) |
| Signed release           | **Not produced** — no Developer ID certificate on the build Mac or in CI    |
| Notarized public release | **Not produced** — requires Developer ID + Apple notarization credentials   |

## 2. Installing the development build

1. Open `Kiko_0.1.0_aarch64.dmg` and drag **Kiko** to **Applications**.
2. The first time, **right-click Kiko → Open → Open** (Gatekeeper blocks un-notarized apps
   on double-click). If macOS still refuses: System Settings → Privacy & Security → "Open
   Anyway".
3. In Kiko: **Kiko → Server Connection…**, enter the HTTPS address of the Kiko server and
   confirm the native dialog. (`http://localhost:8000` is only for a server on the same Mac.)
4. Register or sign in.

Requirements: macOS 12+, Apple Silicon.

## 3. Backend compatibility

- Works with the current API (`20261014_0035`), **no backend change or migration**.
- The server must be reachable over HTTPS from the Mac. CORS/`WEB_ORIGINS` need no change
  (the app's requests carry no `Origin`).
- `AUTH_RATE_LIMIT_*` applies per IP as for the web.
- For Kiko AI planning the server needs a configured AI provider; without it the app shows
  the server's "unavailable" response.
- Email verification links point to the web origin; `kiko://verify-email?token=…` is
  supported if the email template is changed to use it.

## 4. Signing and notarization (to do, with owner credentials)

1. Apple Developer Program membership; create a **Developer ID Application** certificate.
2. Store in GitHub Actions secrets: `APPLE_CERTIFICATE` (base64 .p12),
   `APPLE_CERTIFICATE_PASSWORD`, `APPLE_SIGNING_IDENTITY`, `APPLE_ID`, `APPLE_PASSWORD`
   (app-specific), `APPLE_TEAM_ID`. Never commit them.
3. Set `bundle.macOS.signingIdentity` from the secret and run `tauri build`; Tauri signs and
   submits for notarization when the Apple variables are present.
4. Verify with `spctl -a -vv Kiko.app` ("accepted, source=Notarized Developer ID").

## 5. Automatic updates

Not enabled. Enabling requires: a Tauri updater key pair (private key as a CI secret), a
trusted HTTPS feed (e.g. GitHub Releases, private), signed update artifacts, and channels
(`internal`, `beta`, `stable`). Rollback = publish the previous version as latest. The app
never downloads executable code today.

## 6. Known limitations

- Unsigned/un-notarized; Gatekeeper warning on first open.
- Apple Silicon only; no Intel or universal build yet.
- Online-first: no offline queue; writes fail clearly while offline.
- Notifications are polled every 60 s while the app runs; no push and nothing runs after quit.
- No menu-bar companion.
- Sessions appear in Settings → Sessions like web sessions (no per-device name yet).
- Real-provider integrations (Gmail, Calendar, GitHub, Codex, AI) not exercised from desktop.
- Brand icon is a placeholder (`apps/desktop/assets/icon-source.png`).
- See `KIKO-MACOS-TESTING.md` §5 for unverified areas.

## 7. Readiness assessment

**NOT READY — BLOCKERS REMAIN** (for intensive owner testing against real operations)

The application itself runs, authenticates, persists sessions securely, and completed the
governed journey end to end in the real app bundle. The remaining blockers are outside the
app code:

| #   | Blocker                                                         | Owner action                     |
| --- | --------------------------------------------------------------- | -------------------------------- |
| B1  | PR #31 (commercial release) not merged into `main`              | Merge PR #31                     |
| B2  | No authorized HTTPS staging backend for the Mac to connect to   | Provide/authorize staging        |
| B3  | Kiko AI planning not verified with a real provider from desktop | Enable an AI provider on staging |
| B4  | Signing/notarization for distribution beyond the owner's Mac    | Apple Developer ID credentials   |

With B1–B3 resolved, the same build can be used immediately for owner testing; B4 is needed
only for distribution to other people.
