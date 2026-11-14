# Kiko for macOS — architecture

**Status:** implemented on `feat/kiko-macos-desktop` (2026-11-14).  
**Scope:** the macOS client. The FastAPI backend stays the only business execution service.

## 1. Decision: Tauri 2 (over Electron and alternatives)

| Criterion                     | Tauri 2 (chosen)                                         | Electron                                            | Native SwiftUI rewrite             |
| ----------------------------- | -------------------------------------------------------- | --------------------------------------------------- | ---------------------------------- |
| Reuse of the existing Kiko UI | Full (Next.js static export in WKWebView)                | Full                                                | None — every module rebuilt        |
| Bundle size (measured)        | **7.4 MB app, 5.0 MB DMG**                               | larger: bundles Chromium + Node (not measured here) | Small                              |
| Memory at idle (measured)     | ~95 MB app process + ~85 MB WebKit content               | higher: Chromium processes (not measured here)      | Lowest                             |
| Privilege model               | Deny-by-default capabilities; explicit Rust commands     | Node in main process; must harden manually          | Native                             |
| Windows path (P2)             | Same code base (WebView2)                                | Same code base                                      | Separate rewrite                   |
| Risk                          | WKWebView quirks (found: async `confirm`, custom scheme) | Larger attack surface, frequent Chromium CVEs       | Months of rework, two UIs to staff |

Tauri met every requirement in validation (static export served, IPC, Keychain, menus, deep
links, notifications, DMG), so it was adopted. Electron remains a fallback if a WebKit-only
defect proves unfixable.

## 2. Component map

```
┌───────────────────────── Kiko.app (Tauri 2, Rust) ─────────────────────────┐
│  WKWebView  ── kikoui://localhost ──►  bundled UI (apps/web static export)  │
│      │ IPC (validated commands only)                                        │
│      ▼                                                                      │
│  api.rs  ── HTTPS ──► Kiko API (FastAPI)   keychain.rs ── macOS Keychain     │
│  protocol.rs  menu.rs  deep_link.rs  commands.rs  config.rs                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

- `apps/web` is **one UI code base** for Web and macOS. A build-time platform flag
  (`NEXT_PUBLIC_KIKO_PLATFORM=desktop`) switches the transport, downloads, OAuth hand-off,
  confirmations and the desktop shell. The web build is functionally unchanged.
- `apps/desktop/src-tauri` holds all native code. Business rules never live here.

## 3. UI delivery: static export + `kikoui://` protocol

- `scripts/build-ui.mjs` runs `next build` with `NEXT_OUTPUT_MODE=export` and copies `out/`
  into the bundle.
- The 13 dynamic routes (`[id]` …) are server wrappers that pre-render one placeholder page
  (`__kiko__`) in the desktop export only; `lib/route-params.ts` reads the real identifier
  from the URL. `protocol.rs` serves `/dashboard/tasks/<id>/` from
  `/dashboard/tasks/__kiko__/index.html` (and the matching RSC `.txt` payloads).
- Asset lookup is exact (Tauri's resolver would otherwise fall back to `index.html`) and
  path traversal is rejected before lookup.

## 4. Network and session model

1. The WebView never performs network I/O to the API. Every call goes through
   `invoke('api_request')`.
2. `api.rs` accepts only `GET|POST|PUT|PATCH|DELETE`, only relative `/api/v1/…` or `/health`
   paths (no `..`, `//`, `\`, control characters), only `accept`, `content-type`,
   `idempotency-key` headers, bodies ≤ 25 MiB, and follows **no redirects**.
3. Sign-in uses the existing `/api/v1/auth/login` endpoint. Rust captures the access token
   from the body (replacing it with `desktop-managed` before the UI sees the response) and
   the `agent_refresh_token` from `Set-Cookie`, which it stores in the **macOS Keychain**
   (service `pt.pixart.kiko.session`, account = API origin).
4. Rust attaches `Authorization` to API calls and the refresh cookie only to
   `/auth/refresh` and `/auth/logout`. On `401` it refreshes once and retries.
5. Backend rotation and reuse detection are unchanged; a cleared cookie or a failed refresh
   deletes the Keychain item. Logout and password change clear it too.
6. Only `GET`/`HEAD` are retried, once, on connection-level failures. Writes are never
   repeated automatically.

**No backend change was required.** Native requests carry no `Origin` header, so
`require_allowed_origin` and CORS do not need a desktop origin.

Future (documented, not required): `/api/v1/auth/native/*` returning tokens in the body with a
device label, so sessions can be named and revoked per Mac.

## 5. Native capabilities and permissions

| Capability         | Implementation                                                         | JS permission                      |
| ------------------ | ---------------------------------------------------------------------- | ---------------------------------- |
| Menus & shortcuts  | `menu.rs` (App, File, Edit, View, Go, Window); ⌘1–8, ⌘K, ⌘N, ⌘, ⌘[ ⌘]  | event listen/unlisten              |
| Window state       | `tauri-plugin-window-state` (size/position); last route in storage     | —                                  |
| Title bar drag     | overlay title bar + drag region                                        | `core:window:allow-start-dragging` |
| Notifications      | UI polls `/notifications` every 60 s; new items → `notify` command     | — (Rust command)                   |
| Save files         | `save_file`: native save panel, writes only to the chosen path         | — (Rust command)                   |
| External links     | `open_external`: `https:` and `mailto:` only, system browser           | — (Rust command)                   |
| OAuth (Gmail/Cal.) | provider authorization opens in the system browser                     | — (Rust command)                   |
| Confirmations      | `confirm_action`: native dialog (`window.confirm` is async in WebView) | — (Rust command)                   |
| Server connection  | `set_server_url`: HTTPS (or loopback HTTP), **native confirmation**    | — (Rust command)                   |
| Deep links         | `kiko://open/…`, `verify-email`, `reset-password`, `invite` → routes   | —                                  |

Not exposed: shell, filesystem read, arbitrary HTTP, clipboard plugin, Codex runner, updater.

## 6. Security controls

- CSP on every bundled document: `default-src 'self'`; scripts and styles from the bundle
  only (`'unsafe-inline'` required by the Next.js bootstrap); `connect-src 'self' ipc:`;
  no frames, objects or remote origins.
- Navigation is pinned to `kikoui://`; external links are intercepted and opened in the
  system browser.
- Entitlements: `com.apple.security.network.client` only; hardened runtime enabled.
- Debug-only smoke harness (`smoke.rs`) is compiled out of release builds (verified: no
  harness strings in the release binary).
- A compromised WebView could still call the API **as the signed-in user** (same as XSS on
  the web), but cannot read tokens, change servers silently, write files silently or reach
  other hosts.

## 7. Configuration

Server resolution: `KIKO_API_URL` env → `server.json` in
`~/Library/Application Support/pt.pixart.kiko/` (set in **Kiko → Server Connection…**) →
`KIKO_DEFAULT_API_URL` baked at build → `http://localhost:8000`.

## 8. Platform decisions

- **Apple Silicon first** (`aarch64`). Intel: Tauri supports `x86_64-apple-darwin` and a
  universal binary (`--target universal-apple-darwin`); not built yet because no Intel test
  hardware was available. Add once a test Mac exists.
- **Minimum macOS 12.0.**
- **Updates:** the Tauri updater requires a signing key and a trusted feed; it is
  intentionally **not enabled** until both exist (see release readiness).

## 9. Future Windows and Web

- Windows (P2): same Rust crate. Replace Keychain with Windows Credential Manager (the
  `keyring` crate already abstracts it), switch the deep-link handler to single-instance
  arguments (already wired), and build MSI/NSIS on a Windows runner.
- Web (P3): the existing Next.js product remains the web client; desktop changes are behind
  the platform flag. Shared domain types live in `packages/shared`.
- A typed OpenAPI client package is the next step for shared contracts; today all calls are
  centralised in `apps/web/lib/*-client.ts` over one transport (`apiFetch`).
