import { confirmNative } from './desktop-bridge';
import { isDesktop } from './platform';

/**
 * Ask the user to confirm a destructive action. Desktop uses a native macOS dialog
 * (`window.confirm` resolves asynchronously inside the Tauri WebView and cannot be trusted
 * to block). Web keeps the browser dialog.
 */
export async function confirmAction(message: string): Promise<boolean> {
  if (isDesktop) return confirmNative(message);
  // eslint-disable-next-line no-restricted-properties -- the one sanctioned web fallback
  return window.confirm(message);
}
