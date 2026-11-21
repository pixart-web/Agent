import React from 'react';

import { KikoAvatar } from './kiko-avatar';

/** Kiko brand: the character mark with the wordmark. */
export function KikoLogo({ size = 52 }: { size?: number }) {
  return (
    <div className="kiko-logo">
      <KikoAvatar state="idle" size={size} decorative />
      <span className="kiko-logo__text">
        <strong>Kiko</strong>
        <span>AI Operating System</span>
      </span>
    </div>
  );
}
