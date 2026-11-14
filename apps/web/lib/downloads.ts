import { openExternal, saveFile } from './desktop-bridge';
import { isDesktop } from './platform';

/**
 * Save a downloaded file. Web: browser download. Desktop: native save panel; nothing is
 * written unless the user picks a destination. Resolves to `false` if the user cancels.
 */
export async function saveDownload(
  blob: Blob,
  fileName: string,
): Promise<boolean> {
  if (isDesktop) {
    return (await saveFile(fileName, blob)) !== null;
  }
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
  return true;
}

/**
 * Continue a provider authorization (OAuth) flow. Desktop opens the system browser so
 * provider sign-in never happens inside the app's WebView.
 */
export async function startExternalAuthorization(url: string): Promise<void> {
  if (isDesktop) {
    await openExternal(url);
    return;
  }
  window.location.assign(url);
}
