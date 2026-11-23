import type { TaskAction } from '@agent/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ActionProposalPreview } from '../components/task-agent-panel';

const action: TaskAction = {
  id: 'action-calendar',
  task_id: 'task-1',
  tool_name: 'calendar.create_event',
  tool_version: '1',
  input_payload: {
    account_id: 'account-1',
    calendar_id: 'primary',
    title: 'Customer review',
    start: {
      date_time: '2026-10-25T09:00:00+00:00',
      time_zone: 'Europe/Lisbon',
    },
    end: { date_time: '2026-10-25T10:00:00+00:00', time_zone: 'Europe/Lisbon' },
    location: 'Video call',
    attendees: ['customer@example.net'],
  },
  risk_level: 'yellow',
  status: 'waiting_approval',
  created_by_type: 'agent',
  created_by_id: null,
  action_fingerprint: 'fingerprint',
  correlation_id: 'correlation',
  created_at: '2026-09-19T10:00:00Z',
  updated_at: '2026-09-19T10:00:00Z',
};

describe('calendar action UI', () => {
  it('shows the complete governed event preview and approval requirement', () => {
    const markup = renderToStaticMarkup(
      <ActionProposalPreview action={action} />,
    );

    expect(markup).toContain('Criar evento de calendário');
    expect(markup).toContain('Conta: account-1');
    expect(markup).toContain('Calendário: primary');
    expect(markup).toContain('Título: Customer review');
    expect(markup).toContain('Europe/Lisbon');
    expect(markup).toContain('Local: Video call');
    expect(markup).toContain('Participantes: customer@example.net');
    expect(markup).toContain('Risco: Amarelo');
    expect(markup).toContain('Requer aprovação: Sim');
  });
});
