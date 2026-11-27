'use client';

import React, { FormEvent, useEffect, useState } from 'react';

import { failureMessage } from '../lib/api-messages';
import { label } from '../lib/labels';
import {
  checkPixartAppHealth,
  listPixartApps,
  registerPixartApp,
  updatePixartApp,
  type PixartApp,
  type PixartAppStatus,
} from '../lib/platform-admin-client';

const STATUSES: PixartAppStatus[] = [
  'unsupported',
  'requires_setup',
  'available',
  'unavailable',
];

/** Platform admin: register Pixart products and record their API contract. */
export function PixartAppsAdmin() {
  const [apps, setApps] = useState<PixartApp[]>([]);
  const [key, setKey] = useState('');
  const [name, setName] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    void listPixartApps()
      .then(setApps)
      .catch((failure) =>
        setMessage(
          failureMessage(failure, 'Não foi possível carregar os produtos.'),
        ),
      );
  }, []);

  function replace(app: PixartApp) {
    setApps((items) => items.map((item) => (item.id === app.id ? app : item)));
  }

  async function act(action: () => Promise<void>, fallback: string) {
    setMessage('');
    try {
      await action();
    } catch (failure) {
      setMessage(failureMessage(failure, fallback));
    }
  }

  function register(event: FormEvent) {
    event.preventDefault();
    void act(async () => {
      const app = await registerPixartApp({
        key: key.trim(),
        name: name.trim(),
        base_url: baseUrl.trim() || null,
      });
      setApps((items) =>
        [...items, app].sort((a, b) => a.name.localeCompare(b.name)),
      );
      setKey('');
      setName('');
      setBaseUrl('');
    }, 'Não foi possível registar o produto.');
  }

  return (
    <section className="workflow-panel" aria-labelledby="pixart-apps-title">
      <div className="workflow-panel__heading">
        <h2 id="pixart-apps-title">Produtos Pixart</h2>
      </div>
      <p className="form-hint">
        Um produto só pode ficar “Disponível” depois de registado o contrato da
        API (endereço, versão e documentação). O Kiko ainda não liga dados a
        nenhum produto: este registo prepara essas ligações.
      </p>
      <form className="workflow-form pixart-app-form" onSubmit={register}>
        <label>
          Chave
          <input
            required
            pattern="[a-z0-9][a-z0-9-]*"
            placeholder="web-content-flow"
            value={key}
            onChange={(event) => setKey(event.target.value)}
          />
        </label>
        <label>
          Nome
          <input
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label>
          Endereço (opcional)
          <input
            type="url"
            placeholder="https://"
            value={baseUrl}
            onChange={(event) => setBaseUrl(event.target.value)}
          />
        </label>
        <button className="primary-button" type="submit">
          Registar produto
        </button>
      </form>
      {apps.length === 0 ? (
        <p className="empty-state">Ainda não há produtos registados.</p>
      ) : (
        <ul className="pixart-app-list">
          {apps.map((app) => (
            <li key={app.id} className="pixart-app-row">
              <div>
                <strong>{app.name}</strong>{' '}
                <span className="form-hint">{app.key}</span>
                <p className="form-hint">
                  {app.base_url ?? 'Sem endereço'}
                  {app.api_version ? ` · API ${app.api_version}` : ''}
                  {app.last_health_status
                    ? ` · ${label(app.last_health_status)}`
                    : ''}
                </p>
              </div>
              <select
                aria-label={`Estado de ${app.name}`}
                value={app.status}
                onChange={(event) =>
                  void act(
                    async () =>
                      replace(
                        await updatePixartApp(app.id, {
                          status: event.target.value as PixartAppStatus,
                        }),
                      ),
                    'Não foi possível mudar o estado.',
                  )
                }
              >
                {STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {label(status)}
                  </option>
                ))}
              </select>
              <button
                className="secondary-button"
                type="button"
                disabled={!app.base_url}
                onClick={() =>
                  void act(
                    async () => replace(await checkPixartAppHealth(app.id)),
                    'Não foi possível verificar o estado.',
                  )
                }
              >
                Verificar estado
              </button>
            </li>
          ))}
        </ul>
      )}
      {message ? (
        <p className="workflow-alert" role="status">
          {message}
        </p>
      ) : null}
    </section>
  );
}
