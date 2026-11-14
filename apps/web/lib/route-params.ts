'use client';

import { useParams as useNextParams, usePathname } from 'next/navigation';
import { useMemo } from 'react';

import { STATIC_PARAM_PLACEHOLDER } from './static-route-params';

type Params = Record<string, string | string[]>;

/**
 * Replace the static-export placeholder with the real identifier from the URL.
 *
 * Desktop builds pre-render every dynamic route once, with a placeholder segment.
 * All dynamic routes in this app are leaf segments, so the real value is the last
 * non-empty path segment of the current URL.
 */
export function resolveRouteParams<T extends Params>(
  params: T,
  pathname: string | null,
): T {
  const placeholderKeys = Object.keys(params).filter(
    (key) => params[key] === STATIC_PARAM_PLACEHOLDER,
  );
  if (placeholderKeys.length === 0 || !pathname) return params;
  const segments = pathname.split('/').filter(Boolean);
  const last = segments.at(-1);
  if (!last || last === STATIC_PARAM_PLACEHOLDER) return params;
  const resolved: Params = { ...params };
  for (const key of placeholderKeys) {
    resolved[key] = safeDecode(last);
  }
  return resolved as T;
}

function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

/** Drop-in replacement for `next/navigation`'s `useParams` that works in desktop exports. */
export function useParams<T extends Params = Params>(): T {
  const params = useNextParams<T>();
  const pathname = usePathname();
  return useMemo(
    () => resolveRouteParams(params, pathname),
    [params, pathname],
  );
}
