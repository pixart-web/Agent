/** Which client this bundle was built for. Set by the desktop build (apps/desktop). */
export type KikoPlatform = 'web' | 'desktop';

export const KIKO_PLATFORM: KikoPlatform =
  process.env.NEXT_PUBLIC_KIKO_PLATFORM === 'desktop' ? 'desktop' : 'web';

export const isDesktop = KIKO_PLATFORM === 'desktop';
