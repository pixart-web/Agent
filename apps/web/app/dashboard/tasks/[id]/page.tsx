import { staticRouteParams } from '../../../../lib/static-route-params';
import { Suspense } from 'react';

import ClientPage from './page-client';

// Server wrapper so the desktop static export can pre-render a placeholder page
// (see lib/static-route-params.ts). It must render the client page rather than
// re-export it, or Next.js ignores generateStaticParams.
export function generateStaticParams() {
  return staticRouteParams('id');
}

export default function Page() {
  return (
    <Suspense fallback={<main className="loading-page">A carregar…</main>}>
      <ClientPage />
    </Suspense>
  );
}
