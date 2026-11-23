import React, { useId } from 'react';

import { KIKO_STATE_COPY, type KikoState } from '../../lib/kiko-state';

/**
 * The Kiko character, drawn in SVG after the official logo (domed head with a large dark
 * visor, headphone ears with amber rings, small body with an amber core and an
 * amber-to-violet orbit) and animated with CSS. Every state is driven by the caller from
 * real application data (see `deriveKikoState`). With reduced motion the character is
 * static; the state is always also given as text by the caller.
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
  const body = `kiko-body-${id}`;
  const visor = `kiko-visor-${id}`;
  const orbit = `kiko-orbit-${id}`;
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
        <radialGradient id={shell} cx="34%" cy="22%" r="85%">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="42%" stopColor="#E6E0F1" />
          <stop offset="78%" stopColor="#A89FC2" />
          <stop offset="100%" stopColor="#5D5478" />
        </radialGradient>
        <radialGradient id={body} cx="40%" cy="20%" r="90%">
          <stop offset="0%" stopColor="#F4F0FA" />
          <stop offset="60%" stopColor="#B9B0CF" />
          <stop offset="100%" stopColor="#5A5274" />
        </radialGradient>
        <radialGradient id={visor} cx="40%" cy="30%" r="80%">
          <stop offset="0%" stopColor="#2A2338" />
          <stop offset="55%" stopColor="#120F1C" />
          <stop offset="100%" stopColor="#050409" />
        </radialGradient>
        <linearGradient id={orbit} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#FFB067" />
          <stop offset="55%" stopColor="#FF8A3D" />
          <stop offset="100%" stopColor="#A66CFF" />
        </linearGradient>
        <radialGradient id={glow} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#FF995F" stopOpacity="0.85" />
          <stop offset="100%" stopColor="#FF995F" stopOpacity="0" />
        </radialGradient>
      </defs>

      <ellipse
        className="kiko-avatar__shadow"
        cx="124"
        cy="250"
        rx="58"
        ry="6"
      />

      <g className="kiko-avatar__float">
        {/* Status ring: spins while executing, pulses while waiting for approval. */}
        <circle className="kiko-avatar__ring" cx="124" cy="120" r="106" />

        <g className="kiko-avatar__body">
          <path
            d="M72 230 C66 196 88 170 126 168 C164 170 186 196 180 228 Q128 238 72 230 Z"
            fill={`url(#${body})`}
          />
          <path
            d="M84 228 C80 210 86 194 98 186 C92 202 92 218 96 230 Z"
            fill="#7C7398"
            opacity="0.5"
          />
          <circle
            className="kiko-avatar__core-glow"
            cx="136"
            cy="212"
            r="20"
            fill={`url(#${glow})`}
          />
          <circle className="kiko-avatar__core" cx="136" cy="212" r="12" />
        </g>

        {/* The orbit: one swoosh, thick at the bottom and tapering at both ends. */}
        <path
          className="kiko-avatar__orbit"
          d="M16 170 C-8 220 66 248 134 242 C196 236 238 214 230 174 C222 206 190 228 134 232 C76 238 8 214 16 170 Z"
          fill={`url(#${orbit})`}
        />

        <g className="kiko-avatar__head">
          {/* Slight three-quarter tilt, as in the logo. */}
          <g transform="rotate(6 126 112)">
            {/* Far ear (partly hidden by the head). */}
            <ellipse
              cx="207"
              cy="110"
              rx="12"
              ry="23"
              className="kiko-avatar__ear"
            />
            <ellipse
              cx="208"
              cy="110"
              rx="8"
              ry="18"
              className="kiko-avatar__ear-light"
            />

            <path
              d="M38 118 C34 66 78 30 130 30 C182 30 214 64 212 110 C210 146 184 164 132 166 C78 168 42 156 38 118 Z"
              fill={`url(#${shell})`}
            />
            <path
              className="kiko-avatar__visor"
              d="M70 98 C72 68 102 54 140 56 C176 58 200 80 198 108 C196 134 176 148 140 150 C104 152 74 140 70 118 Z"
              fill={`url(#${visor})`}
            />
            <path
              d="M88 70 C104 60 130 56 156 60"
              className="kiko-avatar__glare"
            />

            {/* Near ear: a headphone cup with an amber ring. */}
            <circle cx="54" cy="122" r="30" className="kiko-avatar__ear" />
            <circle
              cx="54"
              cy="122"
              r="22"
              className="kiko-avatar__ear-light"
            />
            <circle cx="51" cy="123" r="14" className="kiko-avatar__ear-cup" />

            <g className="kiko-avatar__eyes">
              {state === 'sleeping' || state === 'offline' ? (
                <>
                  <path d="M104 106 H128" className="kiko-avatar__eye-line" />
                  <path d="M152 103 H176" className="kiko-avatar__eye-line" />
                </>
              ) : state === 'error' ? (
                <>
                  <path
                    d="M104 112 Q116 98 128 108"
                    className="kiko-avatar__eye-line"
                  />
                  <path
                    d="M152 105 Q164 95 176 109"
                    className="kiko-avatar__eye-line"
                  />
                </>
              ) : state === 'listening' || state === 'waiting_approval' ? (
                <>
                  <ellipse
                    cx="116"
                    cy="102"
                    rx="9"
                    ry="11"
                    className="kiko-avatar__eye-dot"
                  />
                  <ellipse
                    cx="164"
                    cy="99"
                    rx="9"
                    ry="11"
                    className="kiko-avatar__eye-dot"
                  />
                </>
              ) : state === 'planning' ? (
                <>
                  <ellipse
                    cx="111"
                    cy="97"
                    rx="7"
                    ry="9"
                    className="kiko-avatar__eye-dot kiko-avatar__glance"
                  />
                  <ellipse
                    cx="159"
                    cy="94"
                    rx="7"
                    ry="9"
                    className="kiko-avatar__eye-dot kiko-avatar__glance"
                  />
                </>
              ) : state === 'thinking' ? (
                <>
                  <circle
                    cx="116"
                    cy="104"
                    r="5"
                    className="kiko-avatar__eye-dot kiko-avatar__think kiko-avatar__think--1"
                  />
                  <circle
                    cx="139"
                    cy="103"
                    r="5"
                    className="kiko-avatar__eye-dot kiko-avatar__think kiko-avatar__think--2"
                  />
                  <circle
                    cx="162"
                    cy="101"
                    r="5"
                    className="kiko-avatar__eye-dot kiko-avatar__think kiko-avatar__think--3"
                  />
                </>
              ) : (
                <>
                  <path
                    d="M102 110 Q116 91 130 110"
                    className="kiko-avatar__eye-line"
                  />
                  <path
                    d="M150 106 Q164 87 178 106"
                    className="kiko-avatar__eye-line"
                  />
                </>
              )}
            </g>
            {state === 'success' ? (
              <path
                d="M126 128 Q140 138 154 127"
                className="kiko-avatar__eye-line kiko-avatar__smile"
              />
            ) : null}
          </g>
        </g>
      </g>
    </svg>
  );
}
