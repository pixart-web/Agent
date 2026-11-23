import Image from 'next/image';
import React from 'react';

/** The Kiko logo (mark + "Kiko · AI Operating System"), from the official artwork. */
export function KikoLogo({
  width = 260,
  priority = true,
}: {
  width?: number;
  priority?: boolean;
}) {
  return (
    <Image
      className="kiko-logo"
      src="/brand/kiko-logo.png"
      width={width}
      height={Math.round((width * 290) / 720)}
      priority={priority}
      alt="Kiko — AI Operating System"
    />
  );
}

/** The robot mark alone, for compact places (collapsed navigation). */
export function KikoMark({ size = 40 }: { size?: number }) {
  return (
    <Image
      className="kiko-mark"
      src="/brand/kiko-mark.png"
      width={size}
      height={Math.round((size * 160) / 192)}
      alt=""
      aria-hidden="true"
    />
  );
}
