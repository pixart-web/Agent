'use client';

import type {
  CrmClient,
  CrmContact,
  CrmOpportunity,
  CrmOrganization,
  CrmPipeline,
} from '@agent/shared';
import Link from 'next/link';
import { FormEvent, useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  confirmCrmImport,
  createCrmClient,
  createCrmContact,
  createCrmOrganization,
  createCrmPipeline,
  downloadCrmExport,
  listCrmClients,
  listCrmOrganizations,
  listCrmOpportunities,
  listCrmPipelines,
  previewCrmImport,
  searchCrmContacts,
  updateCrmOpportunity,
} from '../../../lib/workflow-client';
import type { CrmImportPreview } from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import { CanEdit, EditFieldset } from '../../../lib/workspace-access';
import { label } from '../../../lib/labels';

export default function CrmPage() {
  const { user, loading } = useAuthenticatedUser();
  const [query, setQuery] = useState('');
  const [clients, setClients] = useState<CrmClient[]>([]);
  const [contacts, setContacts] = useState<CrmContact[]>([]);
  const [organizations, setOrganizations] = useState<CrmOrganization[]>([]);
  const [pipelines, setPipelines] = useState<CrmPipeline[]>([]);
  const [opportunities, setOpportunities] = useState<CrmOpportunity[]>([]);
  const [createMode, setCreateMode] = useState<'organization' | 'contact'>(
    'organization',
  );
  const [name, setName] = useState('');
  const [organizationId, setOrganizationId] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [email, setEmail] = useState('');
  const [saving, setSaving] = useState(false);
  const [pipelineName, setPipelineName] = useState('Pipeline de vendas');
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importPreview, setImportPreview] = useState<CrmImportPreview | null>(
    null,
  );
  const [error, setError] = useState('');

  async function refresh(search = '') {
    setError('');
    try {
      const clientResult = await listCrmClients(search);
      const contactResult = await searchCrmContacts(search);
      const organizationResult = await listCrmOrganizations(search);
      const pipelineResult = await listCrmPipelines();
      const allOpportunities: CrmOpportunity[] = [];
      for (const client of clientResult.clients) {
        allOpportunities.push(
          ...(await listCrmOpportunities(client.id)).opportunities,
        );
      }
      setClients(clientResult.clients);
      setContacts(contactResult.contacts);
      setOrganizations(organizationResult.organizations);
      setPipelines(pipelineResult.pipelines);
      setOpportunities(allOpportunities);
    } catch {
      setError('Não foi possível carregar os registos do CRM.');
    }
  }

  async function createRecord(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      if (createMode === 'organization') {
        const organization = await createCrmOrganization({ name });
        await createCrmClient({ organization_id: organization.id });
      } else {
        await createCrmContact({
          full_name: name,
          organization_id: organizationId || undefined,
          job_title: jobTitle || undefined,
          methods: email
            ? [{ method_type: 'email', value: email, is_primary: true }]
            : [],
        });
      }
      setName('');
      setJobTitle('');
      setEmail('');
      await refresh(query.trim());
    } catch {
      setError(
        'Não foi possível criar o registo no CRM. Verifica duplicados e campos inválidos.',
      );
    } finally {
      setSaving(false);
    }
  }

  async function createPipeline(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      await createCrmPipeline({
        name: pipelineName,
        is_default: pipelines.length === 0,
        stages: [
          { name: 'Lead', position: 1, default_probability: 10 },
          { name: 'Qualificado', position: 2, default_probability: 40 },
          { name: 'Proposta', position: 3, default_probability: 70 },
          {
            name: 'Ganho',
            position: 4,
            default_probability: 100,
            is_terminal: true,
          },
        ],
      });
      await refresh(query.trim());
    } catch {
      setError('Não foi possível criar o pipeline de vendas.');
    } finally {
      setSaving(false);
    }
  }

  async function previewImport() {
    if (!importFile) return;
    setSaving(true);
    setError('');
    try {
      setImportPreview(await previewCrmImport(importFile));
    } catch {
      setError('Não foi possível pré-visualizar esta importação CSV.');
    } finally {
      setSaving(false);
    }
  }

  async function confirmImport() {
    if (!importFile || !importPreview) return;
    setSaving(true);
    setError('');
    try {
      await confirmCrmImport(importFile, importPreview.fingerprint);
      setImportFile(null);
      setImportPreview(null);
      await refresh(query.trim());
    } catch {
      setError(
        'A importação falhou. Pré-visualiza de novo o ficheiro final antes de confirmar.',
      );
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    if (user) void refresh();
  }, [user]);

  if (loading || !user)
    return <main className="loading-page">A carregar os clientes…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Contexto de negócio governado</p>
          <h1>Clientes e CRM</h1>
          <p>
            As notas do CRM e os registos de email e calendário ligados são
            dados de negócio não verificados.
          </p>
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void refresh(query.trim());
          }}
        >
          <label>
            Pesquisar contactos e organizações
            <input
              value={query}
              maxLength={255}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <button className="secondary-button" type="submit">
            Pesquisar
          </button>
        </form>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <CanEdit>
        <section className="workflow-panel crm-create-panel">
          <div>
            <h2>Criar registo no CRM</h2>
            <p>
              Os registos manuais ficam limitados ao workspace e entram na
              auditoria.
            </p>
          </div>
          <form onSubmit={createRecord}>
            <label>
              Tipo de registo
              <select
                value={createMode}
                onChange={(event) =>
                  setCreateMode(
                    event.target.value as 'organization' | 'contact',
                  )
                }
              >
                <option value="organization">Organização e cliente</option>
                <option value="contact">Contacto</option>
              </select>
            </label>
            <label>
              {createMode === 'organization'
                ? 'Nome da organização'
                : 'Nome completo'}
              <input
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            {createMode === 'contact' && (
              <>
                <label>
                  Organização
                  <select
                    value={organizationId}
                    onChange={(event) => setOrganizationId(event.target.value)}
                  >
                    <option value="">Nenhum</option>
                    {organizations.map((item) => (
                      <option value={item.id} key={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Cargo
                  <input
                    value={jobTitle}
                    onChange={(event) => setJobTitle(event.target.value)}
                  />
                </label>
                <label>
                  Email
                  <input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                  />
                </label>
              </>
            )}
            <button className="primary-button" disabled={saving}>
              {saving ? 'A criar…' : 'Criar'}
            </button>
          </form>
        </section>
      </CanEdit>
      <section className="workflow-panel">
        <div className="crm-panel-heading">
          <div>
            <h2>Pipeline de vendas</h2>
            <p>Move oportunidades entre etapas governadas.</p>
          </div>
          <CanEdit>
            <form onSubmit={createPipeline}>
              <label>
                Novo pipeline
                <input
                  required
                  value={pipelineName}
                  onChange={(event) => setPipelineName(event.target.value)}
                />
              </label>
              <button className="secondary-button" disabled={saving}>
                Criar pipeline
              </button>
            </form>
          </CanEdit>
        </div>
        {pipelines.length ? (
          pipelines.map((pipeline) => (
            <div className="crm-pipeline" key={pipeline.id}>
              {pipeline.stages.map((stage) => (
                <section key={stage.id}>
                  <div>
                    <strong>{stage.name}</strong>
                    <span>
                      {
                        opportunities.filter(
                          (item) =>
                            item.pipeline_id === pipeline.id &&
                            item.stage_id === stage.id,
                        ).length
                      }
                    </span>
                  </div>
                  {opportunities
                    .filter(
                      (item) =>
                        item.pipeline_id === pipeline.id &&
                        item.stage_id === stage.id,
                    )
                    .map((item) => (
                      <article key={item.id}>
                        <strong>{item.title}</strong>
                        <p>
                          {new Intl.NumberFormat(undefined, {
                            style: 'currency',
                            currency: item.currency,
                          }).format(item.amount_minor / 100)}
                        </p>
                        <span>{item.probability}%</span>
                        <EditFieldset>
                          <label>
                            Etapa
                            <select
                              value={item.stage_id}
                              onChange={async (event) => {
                                const nextStage = pipeline.stages.find(
                                  (value) => value.id === event.target.value,
                                );
                                if (!nextStage) return;
                                await updateCrmOpportunity(item.id, {
                                  stage_id: nextStage.id,
                                  probability: nextStage.default_probability,
                                });
                                await refresh(query.trim());
                              }}
                            >
                              {pipeline.stages.map((value) => (
                                <option value={value.id} key={value.id}>
                                  {value.name}
                                </option>
                              ))}
                            </select>
                          </label>
                        </EditFieldset>
                      </article>
                    ))}
                </section>
              ))}
            </div>
          ))
        ) : (
          <p className="empty-state">
            Nenhum pipeline configurado. Cria um através do Kiko ou da API do
            CRM.
          </p>
        )}
      </section>
      <section className="workflow-panel crm-import-panel">
        <div>
          <h2>Portabilidade de dados</h2>
          <p>
            Importa até 1000 linhas CSV depois de validadas, ou exporta os dados
            do workspace limpos.
          </p>
        </div>
        <CanEdit>
          <label>
            CRM CSV
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => {
                setImportFile(event.target.files?.[0] ?? null);
                setImportPreview(null);
              }}
            />
          </label>
        </CanEdit>
        <div className="button-row">
          <CanEdit>
            <button
              className="secondary-button"
              type="button"
              disabled={!importFile || saving}
              onClick={() => void previewImport()}
            >
              Pré-visualizar importação
            </button>
            <button
              className="primary-button"
              type="button"
              disabled={
                !importPreview || importPreview.invalid_rows > 0 || saving
              }
              onClick={() => void confirmImport()}
            >
              Confirmar importação
            </button>
          </CanEdit>
          <button
            className="text-button"
            type="button"
            onClick={() => void downloadCrmExport('organizations')}
          >
            Exportar organizações
          </button>
          <button
            className="text-button"
            type="button"
            onClick={() => void downloadCrmExport('contacts')}
          >
            Exportar contactos
          </button>
        </div>
        {importPreview && (
          <div className="import-summary" role="status">
            <strong>{importPreview.valid_rows} linhas válidas</strong>
            <span>{importPreview.invalid_rows} linhas precisam de revisão</span>
            {importPreview.rows
              .filter((row) => !row.valid)
              .map((row) => (
                <p key={row.row}>
                  Linha {row.row}: {row.errors.join(', ')}
                </p>
              ))}
          </div>
        )}
      </section>
      <section className="workflow-panel">
        <h2>Clientes</h2>
        <div className="agent-grid">
          {clients.map((client) => (
            <Link
              className="agent-card agent-card--link"
              href={'/dashboard/crm/clients/' + client.id}
              key={client.id}
            >
              <p className="eyebrow">{client.lifecycle_status}</p>
              <h3>{client.organization.name}</h3>
              <p>{client.industry || 'Sem setor'}</p>
            </Link>
          ))}
        </div>
        {clients.length === 0 && (
          <p className="empty-state">Nenhum perfil de cliente encontrado.</p>
        )}
      </section>
      <section className="workflow-panel">
        <h2>Organizações</h2>
        <div className="agent-grid">
          {organizations.map((organization) => (
            <Link
              className="agent-card agent-card--link"
              href={'/dashboard/crm/organizations/' + organization.id}
              key={organization.id}
            >
              <p className="eyebrow">{label(organization.status)}</p>
              <h3>{organization.name}</h3>
              <p>
                {organization.member_count} contactos ·{' '}
                {organization.tags.join(', ') || 'Sem etiquetas'}
              </p>
            </Link>
          ))}
        </div>
        {organizations.length === 0 && (
          <p className="empty-state">Nenhuma organização encontrada.</p>
        )}
      </section>
      <section className="workflow-panel">
        <h2>Contactos</h2>
        <div className="agent-grid">
          {contacts.map((contact) => (
            <Link
              className="agent-card agent-card--link"
              href={'/dashboard/crm/contacts/' + contact.id}
              key={contact.id}
            >
              <p className="eyebrow">{label(contact.status)}</p>
              <h3>{contact.full_name}</h3>
              <p>{contact.job_title || 'Sem cargo'}</p>
              <p>
                {contact.methods.find((method) => method.is_primary)?.value ||
                  'Sem forma de contacto principal'}
              </p>
            </Link>
          ))}
        </div>
        {contacts.length === 0 && (
          <p className="empty-state">Nenhum contacto encontrado.</p>
        )}
      </section>
    </main>
  );
}
