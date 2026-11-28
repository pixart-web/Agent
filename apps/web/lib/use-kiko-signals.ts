'use client';

import { useEffect, useRef, useState } from 'react';

import { apiFetch } from './auth-client';
import type { KikoSignals } from './kiko-state';
import {
  getOperationsOverview,
  type OperationsOverview,
} from './operations-client';
import { getAgentOverview, listCommands } from './workflow-client';

export type KikoLiveData = {
  loaded: boolean;
  apiOnline: boolean | null;
  aiAvailable: boolean | null;
  aiMessage: string | null;
  overview: OperationsOverview | null;
  planningCommands: number;
  refreshedAt: number;
};

const EMPTY: KikoLiveData = {
  loaded: false,
  apiOnline: null,
  aiAvailable: null,
  aiMessage: null,
  overview: null,
  planningCommands: 0,
  refreshedAt: 0,
};

const REFRESH_MS = 20_000;

async function health(): Promise<boolean> {
  try {
    return (await apiFetch('/health')).ok;
  } catch {
    return false;
  }
}

/** One poll of everything Kiko's state depends on. Failures leave a field unknown. */
export async function loadKikoLiveData(): Promise<KikoLiveData> {
  const apiOnline = await health();
  if (!apiOnline)
    return { ...EMPTY, loaded: true, apiOnline, refreshedAt: Date.now() };
  const [overview, agent, planning] = await Promise.all([
    getOperationsOverview().catch(() => null),
    getAgentOverview('support').catch(() => null),
    listCommands({ status: 'planning', limit: 20 }).catch(() => []),
  ]);
  const status = agent?.operational_status;
  return {
    loaded: true,
    apiOnline,
    aiAvailable:
      status === undefined
        ? null
        : status === 'operational' || status === 'sandbox',
    aiMessage: agent?.operational_message ?? null,
    overview,
    planningCommands: planning.length,
    refreshedAt: Date.now(),
  };
}

// The shell and the home screen both follow the same data; share one poll.
let shared: { at: number; data: Promise<KikoLiveData> } | null = null;
const listeners = new Set<(data: KikoLiveData) => void>();

export function refreshKikoLiveData(force = false): Promise<KikoLiveData> {
  const now = Date.now();
  if (force || !shared || now - shared.at > REFRESH_MS / 2) {
    const data = loadKikoLiveData();
    shared = { at: now, data };
    void data.then((value) => listeners.forEach((listener) => listener(value)));
  }
  return shared.data;
}

export function useKikoLiveData(): KikoLiveData {
  const [data, setData] = useState<KikoLiveData>(EMPTY);
  useEffect(() => {
    let active = true;
    const listener = (value: KikoLiveData) => {
      if (active) setData(value);
    };
    listeners.add(listener);
    void refreshKikoLiveData().then(listener);
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void refreshKikoLiveData();
    }, REFRESH_MS);
    return () => {
      active = false;
      listeners.delete(listener);
      window.clearInterval(timer);
    };
  }, []);
  return data;
}

export function signalsFrom(data: KikoLiveData): KikoSignals {
  return {
    apiOnline: data.apiOnline,
    aiAvailable: data.aiAvailable,
    pendingApprovals: data.overview?.pending_approvals ?? 0,
    activeAgentRuns: data.overview?.active_agent_runs ?? 0,
    planningCommands: data.planningCommands,
  };
}

/**
 * Milliseconds since the last pointer or keyboard interaction. Checked every 30 s; an
 * interaction after a long pause updates at once (so Kiko wakes up immediately) without
 * re-rendering on every mouse move.
 */
export function useIdleTime(threshold = 5 * 60_000): number {
  const last = useRef(0);
  const [idle, setIdle] = useState(0);
  const idleRef = useRef(0);
  useEffect(() => {
    last.current = Date.now();
    const update = () => {
      idleRef.current = Math.max(0, Date.now() - last.current);
      setIdle(idleRef.current);
    };
    const touch = () => {
      last.current = Date.now();
      if (idleRef.current >= threshold) update();
    };
    const events = ['pointerdown', 'keydown', 'wheel', 'pointermove'];
    events.forEach((name) =>
      window.addEventListener(name, touch, { passive: true }),
    );
    const timer = window.setInterval(update, 30_000);
    return () => {
      events.forEach((name) => window.removeEventListener(name, touch));
      window.clearInterval(timer);
    };
  }, [threshold]);
  return idle;
}
