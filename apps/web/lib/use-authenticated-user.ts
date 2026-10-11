'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { getCurrentUser } from './auth-client';
import type { User } from './auth-types';

export function useAuthenticatedUser(requireOnboarding = true): {
  user: User | null;
  loading: boolean;
} {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void getCurrentUser()
      .then((currentUser) => {
        if (!currentUser) {
          router.replace('/login');
          return;
        }
        if (requireOnboarding && !currentUser.onboarding_completed_at) {
          router.replace('/onboarding');
          return;
        }
        if (active) {
          setUser(currentUser);
          setLoading(false);
        }
      })
      .catch(() => router.replace('/login'));
    return () => {
      active = false;
    };
  }, [requireOnboarding, router]);

  return { user, loading };
}
