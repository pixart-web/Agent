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

const nextConfig: NextConfig = {
  output:
    process.env.NEXT_OUTPUT_MODE === 'standalone' ? 'standalone' : undefined,
  transpilePackages: ['@agent/shared'],
  async headers() {
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
  },
};

export default nextConfig;
