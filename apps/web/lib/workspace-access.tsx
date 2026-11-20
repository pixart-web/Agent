'use client';

import React, { type ReactNode, useEffect, useState } from 'react';

import {
  getWorkspaceSettings,
  type WorkspaceSettings,
} from './workspace-settings-client';

export type WorkspaceRole = WorkspaceSettings['role'];

/** Viewers read the workspace; every other role may create and change items. */
export function canEdit(role: WorkspaceRole | null): boolean {
  return role !== 'viewer';
}

/** Owners and admins manage the workspace (settings, members, subscription). */
export function canManage(role: WorkspaceRole | null): boolean {
  return role === 'owner' || role === 'admin';
}

// Several components on one page ask at once; share one request for a few seconds. The
// server enforces every rule, so a stale answer only shows or hides a control briefly.
const SHARE_MS = 5000;
let shared: { at: number; role: Promise<WorkspaceRole | null> } | null = null;

export function loadWorkspaceRole(
  now = Date.now(),
): Promise<WorkspaceRole | null> {
  if (!shared || now - shared.at > SHARE_MS) {
    shared = {
      at: now,
      role: getWorkspaceSettings()
        .then((settings) => settings.role)
        .catch(() => null),
    };
  }
  return shared.role;
}

export function resetWorkspaceRole(): void {
  shared = null;
}

type RoleState = { loaded: boolean; role: WorkspaceRole | null };

/** The caller's role in the active workspace (`role` is `null` when it is unknown). */
export function useWorkspaceAccess(): RoleState {
  const [state, setState] = useState<RoleState>({ loaded: false, role: null });
  useEffect(() => {
    let active = true;
    void loadWorkspaceRole().then((role) => {
      if (active) setState({ loaded: true, role });
    });
    return () => {
      active = false;
    };
  }, []);
  return state;
}

/**
 * Renders its children only for members who may change the workspace; viewers see the
 * fallback (nothing by default). Nothing renders while the role loads, so a form never
 * flashes in for a viewer. The API refuses viewer writes regardless.
 */
export function CanEdit({
  children,
  fallback = null,
}: {
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { loaded, role } = useWorkspaceAccess();
  if (!loaded) return null;
  return <>{canEdit(role) ? children : fallback}</>;
}

/** Renders its children only for owners and admins. */
export function CanManage({
  children,
  fallback = null,
}: {
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { loaded, role } = useWorkspaceAccess();
  if (!loaded) return null;
  return <>{canManage(role) ? children : fallback}</>;
}

/**
 * Keeps a form's values visible but disables every control inside it for viewers (and
 * while the role loads), for forms that also show information.
 */
export function EditFieldset({ children }: { children: ReactNode }) {
  const { loaded, role } = useWorkspaceAccess();
  return (
    <fieldset className="edit-fieldset" disabled={!loaded || !canEdit(role)}>
      {children}
    </fieldset>
  );
}
