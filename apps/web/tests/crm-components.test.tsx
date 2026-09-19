import type { TaskAction } from '@agent/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ActionProposalPreview } from '../components/task-agent-panel';

const action: TaskAction = {
  id: 'action-crm',
  task_id: 'task-1',
  tool_name: 'crm.create_contact',
  tool_version: '1',
  input_payload: {
    full_name: 'João Sponsor Demo',
    job_title: 'Commercial Director',
    methods: [{ method_type: 'email', value: 'joao@sponsor-demo.example' }],
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

describe('CRM action UI', () => {
  it('shows the exact governed payload and approval requirement', () => {
    const markup = renderToStaticMarkup(
      <ActionProposalPreview action={action} />,
    );
    expect(markup).toContain('Create CRM Contact');
    expect(markup).toContain('João Sponsor Demo');
    expect(markup).toContain('joao@sponsor-demo.example');
    expect(markup).toContain('Risk: yellow');
    expect(markup).toContain('Requires approval: Yes');
  });
});
