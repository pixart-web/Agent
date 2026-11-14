export function resolveApiBaseUrl(
  nodeEnv: string | undefined,
  configuredUrl: string | undefined,
): string {
  if (nodeEnv === 'production') return '';
  return configuredUrl?.replace(/\/$/, '') ?? 'http://localhost:8000';
}

export const apiBaseUrl = resolveApiBaseUrl(
  process.env.NODE_ENV,
  process.env.NEXT_PUBLIC_API_URL,
);
