/** Segment value used when a dynamic route is pre-rendered for the desktop bundle. */
export const STATIC_PARAM_PLACEHOLDER = '__kiko__';

/**
 * `generateStaticParams` result for a leaf dynamic route.
 *
 * The web server renders dynamic routes on demand, so nothing is pre-rendered there.
 * The desktop static export pre-renders one placeholder page that the desktop shell
 * serves for every concrete identifier.
 */
export function staticRouteParams(param: string): Record<string, string>[] {
  return process.env.KIKO_STATIC_EXPORT === 'true'
    ? [{ [param]: STATIC_PARAM_PLACEHOLDER }]
    : [];
}
