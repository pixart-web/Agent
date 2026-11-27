/**
 * Bridge to the Kiko desktop shell (apps/desktop, Tauri 2).
 *
 * In the desktop app every API call is proxied by Rust: it validates the request,
 * attaches credentials kept outside the WebView (Keychain + process memory) and returns
 * the response. Nothing in this module ever sees an access or refresh token.
 */
import { invoke } from '@tauri-apps/api/core';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';

export const NAVIGATE_EVENT = 'kiko://navigate';
export const COMMAND_EVENT = 'kiko://command';
export const CONNECTIVITY_EVENT = 'kiko:connectivity';

export type DesktopAppInfo = {
  version: string;
  platform: 'macos';
  apiBaseUrl: string;
  hasSession: boolean;
};

type BridgeResponse = {
  status: number;
  headers: [string, string][];
  bodyBase64: string;
};

type BridgeError = { kind: string; message?: string };

// The shell's own detail (network library text, request checks) stays in the logs; screens
// get a Portuguese sentence for each kind of failure.
const BRIDGE_MESSAGES: Record<string, string> = {
  offline: 'Não foi possível contactar o servidor Kiko.',
  timeout: 'O servidor Kiko não respondeu a tempo.',
  storage: 'O Porta-chaves do macOS não está disponível para guardar a sessão.',
  invalid_request: 'O Kiko recusou este pedido por não ser válido.',
};

export class DesktopConnectionError extends TypeError {
  constructor(
    public readonly kind: string,
    message: string,
  ) {
    // TypeError mirrors what `fetch` throws for network failures, so existing error
    // handling treats an unreachable server the same way on web and desktop.
    super(message);
  }
}

function toBase64(bytes: Uint8Array): string {
  let binary = '';
  const chunk = 0x8000;
  for (let index = 0; index < bytes.length; index += chunk) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunk));
  }
  return btoa(binary);
}

function fromBase64(value: string): Uint8Array<ArrayBuffer> {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

function emitConnectivity(online: boolean): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(
    new CustomEvent(CONNECTIVITY_EVENT, { detail: { online } }),
  );
}

const NULL_BODY_STATUSES = new Set([101, 204, 205, 304]);

/** `fetch`-compatible function that sends a Kiko API request through the desktop shell. */
export async function desktopFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  // Let the platform serialise bodies (JSON strings, FormData with a multipart boundary…).
  const request = new Request(new URL(path, 'https://kiko.invalid'), init);
  const method = request.method.toUpperCase();
  const headers: [string, string][] = [];
  request.headers.forEach((value, name) => headers.push([name, value]));
  let bodyBase64: string | undefined;
  if (method !== 'GET' && method !== 'HEAD') {
    const bytes = new Uint8Array(await request.arrayBuffer());
    if (bytes.byteLength > 0) bodyBase64 = toBase64(bytes);
  }
  let result: BridgeResponse;
  try {
    result = await invoke<BridgeResponse>('api_request', {
      request: { method, path, headers, bodyBase64 },
    });
  } catch (error) {
    const bridgeError = error as BridgeError;
    if (bridgeError?.kind === 'offline' || bridgeError?.kind === 'timeout') {
      emitConnectivity(false);
    }
    const kind = bridgeError?.kind ?? 'unknown';
    throw new DesktopConnectionError(
      kind,
      BRIDGE_MESSAGES[kind] ?? BRIDGE_MESSAGES.offline,
    );
  }
  emitConnectivity(true);
  const body = NULL_BODY_STATUSES.has(result.status)
    ? null
    : fromBase64(result.bodyBase64);
  return new Response(body, {
    status: result.status,
    headers: result.headers,
  });
}

export function getAppInfo(): Promise<DesktopAppInfo> {
  return invoke<DesktopAppInfo>('app_info');
}

export function clearDesktopSession(): Promise<void> {
  return invoke('clear_session');
}

export function setServerUrl(url: string): Promise<string> {
  return invoke<string>('set_server_url', { url });
}

export function openExternal(url: string): Promise<void> {
  return invoke('open_external', { url });
}

export function confirmNative(message: string): Promise<boolean> {
  return invoke<boolean>('confirm_action', { message });
}

export function notify(title: string, body: string): Promise<void> {
  return invoke('notify', { title, body });
}

/** Show the native save panel and write the file only where the user chooses. */
export async function saveFile(
  fileName: string,
  blob: Blob,
): Promise<string | null> {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  return invoke<string | null>('save_file', {
    fileName,
    bodyBase64: toBase64(bytes),
  });
}

export function onNavigate(
  handler: (route: string) => void,
): Promise<UnlistenFn> {
  return listen<string>(NAVIGATE_EVENT, (event) => handler(event.payload));
}

/**
 * Deep link that launched the app before the UI was listening (cold start). Call only after
 * `onNavigate` is registered: from then on the shell delivers links as live events.
 */
export function takePendingRoute(): Promise<string | null> {
  return invoke<string | null>('take_pending_route');
}

/** Tell the shell the first usable screen is on display (recorded once per launch). */
export function reportStartup(route: string): Promise<number | null> {
  return invoke<number | null>('report_startup', { route });
}

/**
 * Wait until the page shows real content (no loading placeholder) and report the cold start.
 * Gives up after `timeoutMs`, so a screen stuck loading is not recorded as a fast start.
 */
export function reportWhenReady(route: string, timeoutMs = 20_000): void {
  const started = performance.now();
  const check = () => {
    const ready =
      document.querySelector('main') !== null &&
      document.querySelector('.loading-page') === null;
    if (ready) {
      void reportStartup(route).catch(() => undefined);
      return;
    }
    // setTimeout, not requestAnimationFrame: frames pause while the window is covered.
    if (performance.now() - started < timeoutMs) setTimeout(check, 50);
  };
  setTimeout(check, 0);
}

export function onCommand(
  handler: (command: string) => void,
): Promise<UnlistenFn> {
  return listen<string>(COMMAND_EVENT, (event) => handler(event.payload));
}

export const __test = { toBase64, fromBase64 };
