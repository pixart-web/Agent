'use client';

import qrcode from 'qrcode-generator';
import { FormEvent, useEffect, useMemo, useState } from 'react';

import {
  AuthClientError,
  disableMfa,
  enableMfa,
  getMfaStatus,
  regenerateRecoveryCodes,
  startMfaSetup,
} from '../lib/auth-client';
import type { MfaSetup, MfaStatus } from '../lib/auth-types';

function qrSvg(text: string): string {
  const code = qrcode(0, 'M');
  code.addData(text);
  code.make();
  return code.createSvgTag({ cellSize: 4, margin: 2, scalable: true });
}

function failureText(error: unknown, fallback: string): string {
  return error instanceof AuthClientError ? error.message : fallback;
}

function RecoveryCodes({
  codes,
  onDone,
}: {
  codes: string[];
  onDone: () => void;
}) {
  return (
    <div
      className="mfa-recovery"
      role="region"
      aria-label="Códigos de recuperação"
    >
      <p>
        Guarda estes códigos num local seguro (por exemplo, no gestor de
        palavras-passe). Cada um serve uma vez para entrar sem o telemóvel. Não
        voltam a ser mostrados.
      </p>
      <ul className="mfa-recovery__codes">
        {codes.map((item) => (
          <li key={item}>
            <code>{item}</code>
          </li>
        ))}
      </ul>
      <div className="mfa-actions">
        <button
          className="secondary-button"
          type="button"
          onClick={() => void navigator.clipboard?.writeText(codes.join('\n'))}
        >
          Copiar códigos
        </button>
        <button className="primary-button" type="button" onClick={onDone}>
          Já guardei os códigos
        </button>
      </div>
    </div>
  );
}

/** Settings panel: enable, manage and disable TOTP two-factor authentication. */
export function MfaSettings() {
  const [status, setStatus] = useState<MfaStatus | null>(null);
  const [setup, setSetup] = useState<MfaSetup | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState<'idle' | 'disable' | 'regenerate'>('idle');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void getMfaStatus()
      .then(setStatus)
      .catch(() =>
        setMessage('Não foi possível carregar a verificação em dois passos.'),
      );
  }, []);

  const qr = useMemo(() => (setup ? qrSvg(setup.otpauth_uri) : ''), [setup]);

  async function run(action: () => Promise<void>, fallback: string) {
    setBusy(true);
    setMessage('');
    try {
      await action();
    } catch (error) {
      setMessage(failureText(error, fallback));
    } finally {
      setBusy(false);
    }
  }

  function begin() {
    void run(async () => {
      setSetup(await startMfaSetup());
      setCode('');
    }, 'Não foi possível começar a configuração.');
  }

  function confirmSetup(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      setCodes(await enableMfa(code));
      setSetup(null);
      setCode('');
      setStatus(await getMfaStatus());
    }, 'Não foi possível ativar a verificação em dois passos.');
  }

  function confirmChange(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      if (mode === 'disable') {
        setStatus(await disableMfa(password, code));
        setMessage('Verificação em dois passos desativada.');
      } else {
        setCodes(await regenerateRecoveryCodes(code));
        setStatus(await getMfaStatus());
      }
      setMode('idle');
      setCode('');
      setPassword('');
    }, 'Não foi possível concluir a alteração.');
  }

  return (
    <section
      className="workflow-panel auth-form mfa-settings"
      aria-labelledby="mfa-heading"
    >
      <div className="workflow-panel__heading">
        <h2 id="mfa-heading">Verificação em dois passos</h2>
        {status ? (
          <span
            className={`workflow-badge workflow-badge--${status.enabled ? 'completed' : 'yellow'}`}
          >
            {status.enabled ? 'Ativa' : 'Desativada'}
          </span>
        ) : null}
      </div>
      <p className="form-hint">
        Além da palavra-passe, o Kiko pede um código da app de autenticação do
        telemóvel (Google Authenticator, Microsoft Authenticator, 1Password ou
        Palavras-passe do iPhone).
      </p>

      {codes ? (
        <RecoveryCodes codes={codes} onDone={() => setCodes(null)} />
      ) : null}

      {!codes && status && !status.enabled && !setup ? (
        <button
          className="primary-button"
          type="button"
          disabled={busy}
          onClick={begin}
        >
          Ativar verificação em dois passos
        </button>
      ) : null}

      {setup ? (
        <form className="mfa-setup" onSubmit={confirmSetup} noValidate>
          <ol className="mfa-steps">
            <li>
              Na app de autenticação, adiciona uma conta e lê este código QR.
            </li>
            <li>Indica o código de 6 dígitos que a app mostra.</li>
          </ol>
          <div
            className="mfa-qr"
            role="img"
            aria-label="Código QR para a app de autenticação"
            dangerouslySetInnerHTML={{ __html: qr }}
          />
          <p className="form-hint">
            Não consegues ler o código? Introduz esta chave na app:{' '}
            <code className="mfa-secret">{setup.secret}</code>
          </p>
          <label>
            Código de 6 dígitos
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={8}
              value={code}
              onChange={(event) => setCode(event.target.value)}
            />
          </label>
          <div className="mfa-actions">
            <button
              className="primary-button"
              type="submit"
              disabled={busy || code.trim().length < 6}
            >
              {busy ? 'A ativar…' : 'Ativar'}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => setSetup(null)}
            >
              Cancelar
            </button>
          </div>
        </form>
      ) : null}

      {!codes && status?.enabled && mode === 'idle' ? (
        <>
          <p>
            Ativa desde{' '}
            {status.enabled_at
              ? new Date(status.enabled_at).toLocaleDateString('pt-PT')
              : '—'}
            .{' '}
            {status.recovery_codes_remaining === 1
              ? 'Resta 1 código de recuperação.'
              : `Restam ${status.recovery_codes_remaining} códigos de recuperação.`}
          </p>
          <div className="mfa-actions">
            <button
              className="secondary-button"
              type="button"
              onClick={() => setMode('regenerate')}
            >
              Gerar novos códigos de recuperação
            </button>
            <button
              className="danger-button"
              type="button"
              onClick={() => setMode('disable')}
            >
              Desativar
            </button>
          </div>
        </>
      ) : null}

      {status?.enabled && mode !== 'idle' ? (
        <form className="mfa-setup" onSubmit={confirmChange} noValidate>
          {mode === 'disable' ? (
            <label>
              Palavra-passe atual
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
          ) : null}
          <label>
            Código da app ou de recuperação
            <input
              type="text"
              autoComplete="one-time-code"
              maxLength={32}
              value={code}
              onChange={(event) => setCode(event.target.value)}
            />
          </label>
          <div className="mfa-actions">
            <button
              className={
                mode === 'disable' ? 'danger-button' : 'primary-button'
              }
              type="submit"
              disabled={busy || code.trim().length < 6}
            >
              {mode === 'disable' ? 'Desativar' : 'Gerar códigos'}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                setMode('idle');
                setCode('');
                setPassword('');
              }}
            >
              Cancelar
            </button>
          </div>
        </form>
      ) : null}

      {message ? (
        <p className="form-message" role="status">
          {message}
        </p>
      ) : null}
    </section>
  );
}
