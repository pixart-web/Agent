'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { getCurrentUser } from './auth-client';
import type { User } from './auth-types';

export function useAuthenticatedUser(): {
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
        if (active) {
          setUser(currentUser);
          setLoading(false);
        }
      })
      .catch(() => router.replace('/login'));
    return () => {
      active = false;
    };
  }, [router]);

  return { user, loading };
}
