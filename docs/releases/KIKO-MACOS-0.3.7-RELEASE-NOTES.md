# Kiko for macOS 0.3.7 — release candidate notes

**Status:** release candidate for **owner review** (internal, unsigned).
**Built:** 2026-11-26, branch `release/kiko-0.3.7` (main at `b015272`).

## Changes since 0.3.6

- The macOS menu bar is in European Portuguese: Kiko (Acerca do Kiko, Definições…, Ligação ao
  servidor…, Sair do Kiko), Ficheiro, Editar, Ver, Ir and Janela. The Ir menu uses the same
  names as the in-app navigation. Keyboard shortcuts are unchanged.
- Native dialogs in Portuguese: "Ligar a este servidor Kiko?" (Ligar / Cancelar) and the
  confirmation for destructive actions (Continuar / Cancelar).
- Server address, link and file-save errors in Portuguese; when the server cannot be reached,
  screens show a Portuguese sentence instead of the network library's text.

## Artifact

|          |                                                                                        |
| -------- | -------------------------------------------------------------------------------------- |
| File     | `Kiko_0.3.7_aarch64.dmg` (7,376,519 bytes)                                             |
| SHA-256  | `52545ff90a7e59b54ea64f76c7a520829593540679b5ad9be5df0cfe7754a8c4`                     |
| Requires | Apple Silicon Mac, macOS 12+; 32 GB recommended when the AI model runs on the same Mac |
| Signing  | ad-hoc (hardened runtime); **not** Developer ID signed, **not** notarised              |
