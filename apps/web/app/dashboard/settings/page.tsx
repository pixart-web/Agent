'use client';

import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  AuthClientError,
  changePassword,
  listSessions,
  revokeSession,
  updateProfile,
} from '../../../lib/auth-client';
import type { Session } from '../../../lib/auth-types';
import {
  getNotificationPreferences,
  updateNotificationPreferences,
  type NotificationPreferences,
} from '../../../lib/notification-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import {
  downloadWorkspaceExport,
  getWorkspaceSettings,
  updateWorkspaceSettings,
  type WorkspaceSettings,
} from '../../../lib/workspace-settings-client';
import { label } from '../../../lib/labels';

export default function SettingsPage() {
  const router = useRouter();
  const { user, loading } = useAuthenticatedUser();
  const [fullName, setFullName] = useState('');
  const [language, setLanguage] = useState('en');
  const [timezone, setTimezone] = useState('UTC');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [message, setMessage] = useState('');
  const [notifications, setNotifications] =
    useState<NotificationPreferences | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceSettings | null>(null);

  useEffect(() => {
    if (!user) return;
    setFullName(user.full_name);
    setLanguage(user.language);
    setTimezone(user.timezone);
    void listSessions()
      .then(setSessions)
      .catch(() => setMessage('Não foi possível carregar as sessões.'));
    void getNotificationPreferences()
      .then(setNotifications)
      .catch(() =>
        setMessage('Não foi possível carregar as preferências de notificação.'),
      );
    void getWorkspaceSettings()
      .then(setWorkspace)
      .catch(() =>
        setMessage('Não foi possível carregar as definições do workspace.'),
      );
  }, [user]);

  if (loading || !user)
    return <main className="loading-page">A carregar as definições…</main>;

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    try {
      await updateProfile(fullName.trim(), language, timezone);
      setMessage('Perfil atualizado.');
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Não foi possível atualizar o perfil.',
      );
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    try {
      await changePassword(currentPassword, newPassword);
      router.replace('/login');
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Não foi possível alterar a palavra-passe.',
      );
    }
  }

  async function removeSession(id: string) {
    await revokeSession(id);
    setSessions((items) => items.filter((item) => item.id !== id));
  }

  return (
    <main>
      <DashboardNav user={user} />
      <section className="hero compact-hero">
        <div>
          <p className="eyebrow">Conta</p>
          <h1>Definições</h1>
          {workspace?.is_synthetic_demo ? (
            <p className="status-pill warning">
              Workspace de demonstração — sem dados reais de clientes nem envios
              externos.
            </p>
          ) : null}
        </div>
      </section>
      <section className="workflow-grid">
        <form className="workflow-panel auth-form" onSubmit={saveProfile}>
          <div className="workflow-panel__heading">
            <h2>Perfil</h2>
          </div>
          <label>
            Nome completo
            <input
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
            />
          </label>
          <label>
            Email
            <input value={user.email} disabled />
          </label>
          <label>
            Idioma
            <select
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
            >
              <option value="en">Inglês</option>
              <option value="pt-PT">Português (Portugal)</option>
            </select>
          </label>
          <label>
            Fuso horário
            <input
              value={timezone}
              onChange={(event) => setTimezone(event.target.value)}
            />
          </label>
          <button className="primary-button" type="submit">
            Guardar perfil
          </button>
        </form>
        <form className="workflow-panel auth-form" onSubmit={savePassword}>
          <div className="workflow-panel__heading">
            <h2>Alterar palavra-passe</h2>
          </div>
          <label>
            Palavra-passe atual
            <input
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
            />
          </label>
          <label>
            Nova palavra-passe
            <input
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
            />
          </label>
          <button className="primary-button" type="submit">
            Alterar palavra-passe
          </button>
        </form>
      </section>
      {workspace && (
        <form
          className="workflow-panel auth-form"
          onSubmit={async (event) => {
            event.preventDefault();
            setWorkspace(await updateWorkspaceSettings(workspace));
            setMessage('Definições do workspace atualizadas.');
          }}
        >
          <fieldset
            className="edit-fieldset"
            disabled={!['owner', 'admin'].includes(workspace.role)}
          >
            <div className="workflow-panel__heading">
              <h2>Workspace</h2>
            </div>
            <label>
              Nome
              <input
                value={workspace.name}
                onChange={(event) =>
                  setWorkspace({ ...workspace, name: event.target.value })
                }
              />
            </label>
            <label>
              Descrição
              <textarea
                value={workspace.description ?? ''}
                onChange={(event) =>
                  setWorkspace({
                    ...workspace,
                    description: event.target.value || null,
                  })
                }
              />
            </label>
            <label>
              Setor
              <input
                value={workspace.sector ?? ''}
                onChange={(event) =>
                  setWorkspace({
                    ...workspace,
                    sector: event.target.value || null,
                  })
                }
              />
            </label>
            <label>
              Código do país
              <input
                maxLength={2}
                value={workspace.country ?? ''}
                onChange={(event) =>
                  setWorkspace({
                    ...workspace,
                    country: event.target.value.toUpperCase() || null,
                  })
                }
              />
            </label>
            <label>
              Website
              <input
                type="url"
                value={workspace.website ?? ''}
                onChange={(event) =>
                  setWorkspace({
                    ...workspace,
                    website: event.target.value || null,
                  })
                }
              />
            </label>
            <label>
              Retenção de dados (dias)
              <input
                type="number"
                min={30}
                max={3650}
                value={workspace.retention_days}
                onChange={(event) =>
                  setWorkspace({
                    ...workspace,
                    retention_days: Number(event.target.value),
                  })
                }
              />
            </label>
            <label>
              Limite mensal de tokens de IA
              <input
                type="number"
                min={1000}
                value={workspace.ai_monthly_token_limit ?? ''}
                onChange={(event) =>
                  setWorkspace({
                    ...workspace,
                    ai_monthly_token_limit: event.target.value
                      ? Number(event.target.value)
                      : null,
                  })
                }
              />
            </label>
            <button
              className="primary-button"
              disabled={!['owner', 'admin'].includes(workspace.role)}
            >
              Guardar workspace
            </button>
          </fieldset>
          {!['owner', 'admin'].includes(workspace.role) && (
            <p className="form-hint">
              Só donos e administradores podem alterar as definições do
              workspace.
            </p>
          )}
        </form>
      )}
      {workspace && (
        <section className="workflow-panel">
          <div className="workflow-panel__heading">
            <h2>Equipa e funções</h2>
          </div>
          <div className="activity-list">
            {workspace.members.map((member) => (
              <article className="activity-item" key={member.id}>
                <strong>{member.full_name}</strong>
                <p>
                  {member.email} · {label(member.role)}
                </p>
              </article>
            ))}
          </div>
        </section>
      )}
      {workspace && ['owner', 'admin'].includes(workspace.role) && (
        <section className="workflow-panel">
          <div className="workflow-panel__heading">
            <div>
              <p className="eyebrow">Portabilidade de dados</p>
              <h2>Exportação do workspace</h2>
            </div>
          </div>
          <p className="empty-state">
            Descarrega o perfil do workspace, registos do CRM, projetos, tarefas
            e atividades. Segredos de autenticação e credenciais de integrações
            ficam de fora. Cada exportação fica registada na auditoria.
          </p>
          <div className="button-row">
            <button
              className="primary-button"
              type="button"
              onClick={() =>
                void downloadWorkspaceExport().catch(() =>
                  setMessage(
                    'Não foi possível exportar os dados do workspace.',
                  ),
                )
              }
            >
              Descarregar arquivo JSON
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() =>
                void downloadWorkspaceExport('contacts', 'csv').catch(() =>
                  setMessage('Não foi possível exportar os contactos.'),
                )
              }
            >
              Descarregar contactos (CSV)
            </button>
          </div>
        </section>
      )}
      <section className="workflow-panel settings-sessions">
        <div className="workflow-panel__heading">
          <h2>Sessões ativas</h2>
        </div>
        {sessions.length === 0 ? (
          <p className="empty-state">Sem sessões ativas.</p>
        ) : (
          sessions.map((session) => (
            <article className="settings-session" key={session.id}>
              <div>
                <strong>
                  {session.current ? 'Sessão atual' : 'Sessão iniciada'}
                </strong>
                <p>
                  {session.user_agent ?? 'Dispositivo desconhecido'} ·{' '}
                  {session.ip_address ?? 'IP desconhecido'}
                </p>
              </div>
              {!session.current && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => void removeSession(session.id)}
                >
                  Revogar
                </button>
              )}
            </article>
          ))
        )}
      </section>
      {notifications && (
        <form
          className="workflow-panel auth-form"
          onSubmit={async (event) => {
            event.preventDefault();
            setNotifications(
              await updateNotificationPreferences(notifications),
            );
            setMessage('Preferências de notificação atualizadas.');
          }}
        >
          <div className="workflow-panel__heading">
            <h2>Notificações</h2>
          </div>
          <label>
            <input
              type="checkbox"
              checked={notifications.in_app_enabled}
              onChange={(event) =>
                setNotifications({
                  ...notifications,
                  in_app_enabled: event.target.checked,
                })
              }
            />
            Notificações operacionais na app
          </label>
          <label>
            <input
              type="checkbox"
              checked={notifications.email_enabled}
              onChange={(event) =>
                setNotifications({
                  ...notifications,
                  email_enabled: event.target.checked,
                })
              }
            />
            Notificações por email (requer fornecedor de email configurado)
          </label>
          <button className="primary-button">Guardar preferências</button>
        </form>
      )}
      {message && (
        <p className="form-message settings-message" role="status">
          {message}
        </p>
      )}
    </main>
  );
}
