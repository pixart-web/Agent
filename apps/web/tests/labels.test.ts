import { describe, expect, it } from 'vitest';

import { authMessage } from '../lib/auth-client';
import { label, operationalMessage, serverText } from '../lib/labels';

describe('Portuguese labels', () => {
  it('labels API identifiers and falls back to a readable form', () => {
    expect(label('waiting_approval')).toBe('À espera de aprovação');
    expect(label('high')).toBe('Alta');
    expect(label('sales')).toBe('Vendas');
    expect(label('some_new_state')).toBe('Some new state');
    expect(label(null)).toBe('');
  });

  it('translates server texts, including records stored in English earlier', () => {
    expect(serverText('Approval required')).toBe('Aprovação necessária');
    expect(serverText('Created project Launch')).toBe('Projeto criado: Launch');
    expect(serverText('Linked task 123')).toBe('Tarefa ligada: 123');
    expect(serverText('Projeto criado: Launch')).toBe('Projeto criado: Launch');
    expect(serverText('Something custom')).toBe('Something custom');
  });

  it('translates local-AI status and authentication messages', () => {
    expect(operationalMessage('Local model gemma4 ready')).toBe(
      'Modelo local gemma4 pronto',
    );
    expect(authMessage('Invalid email or password')).toBe(
      'Email ou palavra-passe incorretos.',
    );
    expect(authMessage('Unknown detail')).toBe('Unknown detail');
  });
});
