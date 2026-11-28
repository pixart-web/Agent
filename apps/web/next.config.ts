import type { NextConfig } from 'next';

function connectSources(): string {
  const sources = new Set(["'self'"]);
  const configured = process.env.NEXT_PUBLIC_API_URL;
  if (process.env.NODE_ENV !== 'production' && configured) {
    try {
      sources.add(new URL(configured).origin);
    } catch {
      // Invalid local development URLs are rejected by the runtime API resolver.
    }
  }
  return [...sources].join(' ');
}

function scriptSources(): string {
  return process.env.NODE_ENV === 'production'
    ? "'self' 'unsafe-inline'"
    : "'self' 'unsafe-inline' 'unsafe-eval'";
}

// `export` produces the static UI bundled into the Kiko desktop app (apps/desktop).
// Response headers do not apply to static exports; the desktop shell sets its own CSP.
const isStaticExport = process.env.NEXT_OUTPUT_MODE === 'export';

const nextConfig: NextConfig = {
  // The local test environment runs `next dev` in its own folder so a desktop build
  // (`next build` into .next) cannot break the running dev server.
  distDir: process.env.NEXT_DIST_DIR || '.next',
  output: isStaticExport
    ? 'export'
    : process.env.NEXT_OUTPUT_MODE === 'standalone'
      ? 'standalone'
      : undefined,
  trailingSlash: isStaticExport,
  images: isStaticExport ? { unoptimized: true } : undefined,
  transpilePackages: ['@agent/shared'],
  // `next dev` would otherwise write AGENTS.md/CLAUDE.md into apps/web on every start.
  agentRules: false,
  // Inlined at build time so route modules can decide what to pre-render.
  env: { KIKO_STATIC_EXPORT: isStaticExport ? 'true' : 'false' },
  headers: isStaticExport ? undefined : securityHeaders,
};

async function securityHeaders() {
  return [
    {
      source: '/(.*)',
      headers: [
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        {
          key: 'Permissions-Policy',
          value: 'camera=(), microphone=(), geolocation=(), payment=()',
        },
        {
          key: 'Content-Security-Policy',
          value: [
            "default-src 'self'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "object-src 'none'",
            "img-src 'self' data: blob:",
            "font-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            `script-src ${scriptSources()}`,
            `connect-src ${connectSources()}`,
          ].join('; '),
        },
      ],
    },
  ];
}

export default nextConfig;
