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
    throw new DesktopConnectionError(
      bridgeError?.kind ?? 'unknown',
      bridgeError?.message ?? 'The Kiko server could not be reached.',
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

export function onCommand(
  handler: (command: string) => void,
): Promise<UnlistenFn> {
  return listen<string>(COMMAND_EVENT, (event) => handler(event.payload));
}

export const __test = { toBase64, fromBase64 };
