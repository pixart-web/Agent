# Kiko Alive — Design system

The visual foundation of the Kiko web and macOS clients. Source of truth: the tokens in
`apps/web/app/globals.css` (`:root`) and the components and rules in
`apps/web/app/kiko-alive.css`.

## Principles

1. **Kiko is present, not decorative.** The character shows what the workspace is really
   doing; it never animates fake progress.
2. **Real data or nothing.** Cards without real content are left out. Percentages come from
   plan progress, agent status from the API, activity from notifications and executions.
3. **Dark, warm, restrained.** One warm accent (amber) for action, violet and blue for
   ambient light and system states. Glow is used on the character and the hero only.
4. **Text carries meaning.** Colour, motion and the character always have a text
   equivalent.

## Colour tokens

| Token                | Value                   | Use                                   |
| -------------------- | ----------------------- | ------------------------------------- |
| `--kiko-midnight`    | `#090914`               | Page background                       |
| `--kiko-surface`     | `#151422`               | Elevated surfaces                     |
| `--kiko-surface-2`   | `#1d1b2e`               | Inputs, raised controls               |
| `--kiko-surface-3`   | `#262339`               | Hover, nested surfaces                |
| `--kiko-amber`       | `#ff995f`               | Primary action, links, active accents |
| `--kiko-violet`      | `#8b5cf6`               | Ambient light, planning, active nav   |
| `--kiko-blue`        | `#6b8cff`               | Listening/thinking, informational     |
| `--kiko-text`        | `#f7f5ff`               | Primary text                          |
| `--kiko-text-2`      | `#a8a5b8`               | Secondary text                        |
| `--kiko-line`        | `rgba(255,255,255,.09)` | Hairlines                             |
| `--kiko-line-strong` | `rgba(255,255,255,.16)` | Control borders                       |
| `--kiko-success`     | `#34d399`               | Ready, completed                      |
| `--kiko-warning`     | `#fbbf24`               | Waiting for approval                  |
| `--kiko-danger`      | `#f87171`               | Errors, offline AI                    |

The older names (`--background`, `--surface`, `--ink`, `--muted`, `--line`, `--accent`,
`--accent-soft`, `--healthy`, `--warning`, `--offline`) are aliases of these, so every screen
built before the redesign uses the new theme without code changes. Status badges use tinted
backgrounds (14–18 % of the status colour) with light text of the same hue.

Primary buttons use an amber gradient with **dark text** (`#1d0f06`): white on amber fails
contrast. Body text on surfaces is ≥ 7:1; secondary text ≥ 4.5:1 (checked by the axe sweep).

## Typography

System fonts only (no network fonts; the desktop app works offline): SF Pro Display for
headings, SF Pro Text for UI, falling back to Inter/system-ui elsewhere.

| Role          | Size                         | Weight | Tracking |
| ------------- | ---------------------------- | ------ | -------- |
| Hero title    | clamp(2.2rem, 4vw, 3.4rem)   | 650    | −0.04em  |
| Page title h1 | clamp(2.3rem, 4.2vw, 3.6rem) | 750    | −0.035em |
| Card title    | 1.12rem                      | 700    | −0.01em  |
| Body          | 1rem                         | 400    | 0        |
| Secondary     | 0.8–0.9rem                   | 400    | 0        |
| Eyebrow       | 0.74rem uppercase            | 750    | 0.14em   |

## Spacing, radius, elevation

- Spacing scale: 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 px.
- Radius: 10 px controls (`--radius-control`), 16 px cards (`--radius-card`), 24 px hero
  (`--radius-hero`), full pills for chips and search.
- Elevation: one card shadow (`--shadow-card`), glass surfaces with `backdrop-filter`
  blur 18–24 px; drawers and the palette use a deeper shadow.

## Motion

| Kind        | Duration | Easing                          | Examples                       |
| ----------- | -------- | ------------------------------- | ------------------------------ |
| Feedback    | 160 ms   | `--ease-out` (0.22, 1, 0.36, 1) | Hover, button press, focus     |
| Panels      | 280 ms   | `--ease-out`                    | Rail collapse, drawer slide-in |
| State loops | 1–9 s    | ease-in-out                     | Character float/blink, rings   |
| Ambient     | 18 s     | ease-in-out alternate           | Hero wave drift                |

Every loop lives inside `@media (prefers-reduced-motion: no-preference)`. With reduced
motion the character is static, rings stay visible without spinning, transitions are
removed, and idle main-thread time drops to ~0 % (see the implementation report).

## Focus and keyboard

- A single focus ring: 2 px midnight gap + 2 px amber (`--focus-ring`) on `:focus-visible`.
- Skip link "Saltar para o conteúdo" is the first focusable element on every dashboard page.
- ⌘K / Ctrl+K opens search (the macOS menu sends the same command).
- Escape closes the activity drawer and the search palette.

## Iconography

`KikoIcon` — 24 × 24 line icons, 1.7 px stroke, round joins, drawn for Kiko
(`components/kiko/kiko-icons.tsx`). Always decorative (`aria-hidden`); a text label or
`aria-label` carries the meaning.

## The character

See the UX specification (§ Character). Rendering choice: **SVG + CSS**. It is the cheapest
option that reaches the quality bar, needs no runtime, no GPU scene and no external service,
works offline in the Tauri WebView, and its static frame is the fallback. A 3D (GLB/Three.js)
or Rive version can replace the SVG later behind the same `KikoAvatar` props.
