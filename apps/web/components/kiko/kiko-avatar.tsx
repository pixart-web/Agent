import React, { useId } from 'react';

import { KIKO_STATE_COPY, type KikoState } from '../../lib/kiko-state';

/**
 * The Kiko character: an original small robot drawn in SVG and animated with CSS. Every
 * state is driven by the caller from real application data (see `deriveKikoState`). With
 * reduced motion the character is static; the state is always also given as text by the
 * caller, so the drawing is never the only signal.
 */
export function KikoAvatar({
  state,
  size = 220,
  decorative = false,
}: {
  state: KikoState;
  size?: number;
  decorative?: boolean;
}) {
  const id = useId().replace(/:/g, '');
  const shell = `kiko-shell-${id}`;
  const visor = `kiko-visor-${id}`;
  const glow = `kiko-glow-${id}`;
  const label = `Kiko — ${KIKO_STATE_COPY[state].label}`;

  return (
    <svg
      className={`kiko-avatar kiko-avatar--${state}`}
      data-state={state}
      width={size}
      height={size * (260 / 240)}
      viewBox="0 0 240 260"
      role={decorative ? undefined : 'img'}
      aria-hidden={decorative ? true : undefined}
      aria-label={decorative ? undefined : label}
      focusable="false"
    >
      <defs>
        <radialGradient id={shell} cx="38%" cy="28%" r="80%">
          <stop offset="0%" stopColor="#FBFAFF" />
          <stop offset="55%" stopColor="#C9C5D6" />
          <stop offset="100%" stopColor="#6F6A85" />
        </radialGradient>
        <linearGradient id={visor} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1C1A2C" />
          <stop offset="100%" stopColor="#06060C" />
        </linearGradient>
        <radialGradient id={glow} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#FF995F" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#FF995F" stopOpacity="0" />
        </radialGradient>
      </defs>

      <ellipse
        className="kiko-avatar__shadow"
        cx="120"
        cy="248"
        rx="54"
        ry="7"
      />

      <g className="kiko-avatar__float">
        {/* Status ring: spins while executing, pulses while waiting for approval. */}
        <circle className="kiko-avatar__ring" cx="120" cy="112" r="104" />

        <g className="kiko-avatar__body">
          <ellipse
            cx="72"
            cy="196"
            rx="13"
            ry="22"
            fill={`url(#${shell})`}
            transform="rotate(24 72 196)"
          />
          <ellipse
            cx="168"
            cy="196"
            rx="13"
            ry="22"
            fill={`url(#${shell})`}
            transform="rotate(-24 168 196)"
          />
          <path
            d="M78 182 C78 160 162 160 162 182 L158 214 C154 236 86 236 82 214 Z"
            fill={`url(#${shell})`}
          />
          <circle
            className="kiko-avatar__core-glow"
            cx="120"
            cy="200"
            r="22"
            fill={`url(#${glow})`}
          />
          <circle className="kiko-avatar__core" cx="120" cy="200" r="11" />
        </g>

        <g className="kiko-avatar__head">
          <circle cx="40" cy="104" r="20" className="kiko-avatar__ear" />
          <circle cx="200" cy="104" r="20" className="kiko-avatar__ear" />
          <circle cx="40" cy="104" r="12" className="kiko-avatar__ear-light" />
          <circle cx="200" cy="104" r="12" className="kiko-avatar__ear-light" />
          <rect
            x="44"
            y="34"
            width="152"
            height="138"
            rx="64"
            fill={`url(#${shell})`}
          />
          <rect
            x="60"
            y="56"
            width="120"
            height="94"
            rx="44"
            fill={`url(#${visor})`}
          />
          <path
            d="M76 70 C92 60 120 58 140 62"
            className="kiko-avatar__glare"
          />

          <g className="kiko-avatar__eyes">
            {state === 'sleeping' || state === 'offline' ? (
              <>
                <path d="M86 106 H110" className="kiko-avatar__eye-line" />
                <path d="M130 106 H154" className="kiko-avatar__eye-line" />
              </>
            ) : state === 'error' ? (
              <>
                <path
                  d="M86 112 Q98 98 110 108"
                  className="kiko-avatar__eye-line"
                />
                <path
                  d="M130 108 Q142 98 154 112"
                  className="kiko-avatar__eye-line"
                />
              </>
            ) : state === 'listening' || state === 'waiting_approval' ? (
              <>
                <ellipse
                  cx="98"
                  cy="104"
                  rx="9"
                  ry="11"
                  className="kiko-avatar__eye-dot"
                />
                <ellipse
                  cx="142"
                  cy="104"
                  rx="9"
                  ry="11"
                  className="kiko-avatar__eye-dot"
                />
              </>
            ) : state === 'planning' ? (
              <>
                <ellipse
                  cx="92"
                  cy="98"
                  rx="7"
                  ry="9"
                  className="kiko-avatar__eye-dot kiko-avatar__glance"
                />
                <ellipse
                  cx="136"
                  cy="98"
                  rx="7"
                  ry="9"
                  className="kiko-avatar__eye-dot kiko-avatar__glance"
                />
              </>
            ) : state === 'thinking' ? (
              <>
                <circle
                  cx="96"
                  cy="104"
                  r="5"
                  className="kiko-avatar__eye-dot kiko-avatar__think kiko-avatar__think--1"
                />
                <circle
                  cx="120"
                  cy="104"
                  r="5"
                  className="kiko-avatar__eye-dot kiko-avatar__think kiko-avatar__think--2"
                />
                <circle
                  cx="144"
                  cy="104"
                  r="5"
                  className="kiko-avatar__eye-dot kiko-avatar__think kiko-avatar__think--3"
                />
              </>
            ) : (
              <>
                <path
                  d="M86 110 Q98 94 110 110"
                  className="kiko-avatar__eye-line"
                />
                <path
                  d="M130 110 Q142 94 154 110"
                  className="kiko-avatar__eye-line"
                />
              </>
            )}
          </g>
          {state === 'success' ? (
            <path
              d="M106 128 Q120 138 134 128"
              className="kiko-avatar__eye-line kiko-avatar__smile"
            />
          ) : null}
        </g>
      </g>
    </svg>
  );
}
