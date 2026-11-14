const LAST_ROUTE_KEY = 'kiko.desktop.lastRoute';

/** Only in-app dashboard routes are remembered and restored. */
export function isRestorableRoute(route: string): boolean {
  return (
    /^\/dashboard\/[A-Za-z0-9/_-]*$/.test(route) &&
    !route.includes('//') &&
    route.length <= 300
  );
}

export function rememberRoute(route: string): void {
  if (!isRestorableRoute(route)) return;
  try {
    window.localStorage.setItem(LAST_ROUTE_KEY, route);
  } catch {
    // Storage can be unavailable; restoring the last screen is a convenience only.
  }
}

export function lastRoute(): string | null {
  try {
    const value = window.localStorage.getItem(LAST_ROUTE_KEY);
    return value && isRestorableRoute(value) ? value : null;
  } catch {
    return null;
  }
}
