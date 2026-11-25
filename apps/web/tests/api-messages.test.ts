import { describe, expect, it } from 'vitest';

import { aiErrorHint } from '../lib/ai-errors';
import {
  apiMessage,
  describeApiError,
  readApiError,
} from '../lib/api-messages';

describe('API messages in Portuguese', () => {
  it('translates known messages and keeps unknown ones', () => {
    expect(apiMessage('Workspace edit permission is required')).toBe(
      'Precisas de permissão de edição neste workspace.',
    );
    expect(apiMessage('Approval has already been decided')).toBe(
      'Esta aprovação já foi decidida.',
    );
    expect(apiMessage('Something brand new')).toBe('Something brand new');
  });

  it('translates messages that carry a value', () => {
    expect(apiMessage('Task cannot transition from ready to completed')).toBe(
      'A tarefa não pode passar de pronta para concluída.',
    );
    expect(apiMessage("Local AI model 'gemma4:12b' is not installed")).toBe(
      'O modelo de IA local gemma4:12b não está instalado.',
    );
  });

  it('names the field in request-validation errors', () => {
    expect(
      describeApiError([
        { loc: ['body', 'full_name'], msg: 'Field required', type: 'missing' },
      ]),
    ).toBe('Nome: é obrigatório.');
    expect(
      describeApiError([
        {
          loc: ['body', 'password'],
          msg: 'String should have at least 12 characters',
        },
      ]),
    ).toBe('Palavra-passe: tem de ter pelo menos 12 caracteres.');
    expect(
      describeApiError([
        {
          loc: ['body', 'password'],
          msg: 'Value error, Password must contain at least one number',
        },
      ]),
    ).toBe('A palavra-passe tem de ter pelo menos um número.');
    expect(describeApiError([{}])).toBeNull();
  });

  it('reads a failed response, falling back for non-JSON bodies', async () => {
    const json = new Response(JSON.stringify({ detail: 'Command not found' }), {
      status: 404,
    });
    expect(await readApiError(json, 'Falhou')).toBe('Comando não encontrado.');
    const html = new Response('<html>', { status: 502 });
    expect(await readApiError(html, 'Falhou')).toBe('Falhou');
  });

  it('adds the API reason to the screen message only when the API gave one', async () => {
    const { apiError, failureMessage } = await import('../lib/api-messages');
    const known = await apiError(
      new Response(
        JSON.stringify({
          detail: 'An automation with this name already exists',
        }),
        { status: 409 },
      ),
      'Falhou (409).',
    );
    expect(failureMessage(known, 'Não foi possível guardar.')).toBe(
      'Não foi possível guardar. Já existe uma automatização com este nome.',
    );
    const unknown = await apiError(
      new Response('x', { status: 500 }),
      'Falhou.',
    );
    expect(failureMessage(unknown, 'Não foi possível guardar.')).toBe(
      'Não foi possível guardar.',
    );
    expect(failureMessage(new Error('boom'), 'Não foi possível guardar.')).toBe(
      'Não foi possível guardar.',
    );
  });

  it('keeps the recovery hints for translated AI errors', () => {
    expect(
      aiErrorHint(apiMessage('Local AI runtime is not reachable')),
    ).toMatch(/Ollama/);
    expect(aiErrorHint(apiMessage('Local AI model timed out'))).toMatch(
      /demorou demasiado/,
    );
    expect(
      aiErrorHint(apiMessage("Local AI model 'gemma4:12b' is not installed")),
    ).toContain('ollama pull gemma4:12b');
    expect(aiErrorHint(apiMessage('Gmail request timed out'))).toBeNull();
  });
});
