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
  const [pipelineName, setPipelineName] = useState('Sales pipeline');
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
      setError('Unable to load CRM records.');
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
        'Unable to create the CRM record. Check for duplicates and invalid fields.',
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
          { name: 'Qualified', position: 2, default_probability: 40 },
          { name: 'Proposal', position: 3, default_probability: 70 },
          {
            name: 'Won',
            position: 4,
            default_probability: 100,
            is_terminal: true,
          },
        ],
      });
      await refresh(query.trim());
    } catch {
      setError('Unable to create the sales pipeline.');
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
      setError('Unable to preview this CSV import.');
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
        'Import failed. Preview the final file again before confirming.',
      );
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    if (user) void refresh();
  }, [user]);

  if (loading || !user)
    return <main className="loading-page">Loading clients…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Governed business context</p>
          <h1>Clients & CRM</h1>
          <p>
            CRM notes and linked Email/Calendar records are untrusted business
            data.
          </p>
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void refresh(query.trim());
          }}
        >
          <label>
            Search contacts and organizations
            <input
              value={query}
              maxLength={255}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <button className="secondary-button" type="submit">
            Search
          </button>
        </form>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <section className="workflow-panel crm-create-panel">
        <div>
          <h2>Create CRM record</h2>
          <p>Manual records are tenant-scoped and added to the audit trail.</p>
        </div>
        <form onSubmit={createRecord}>
          <label>
            Record type
            <select
              value={createMode}
              onChange={(event) =>
                setCreateMode(event.target.value as 'organization' | 'contact')
              }
            >
              <option value="organization">Organization & client</option>
              <option value="contact">Contact</option>
            </select>
          </label>
          <label>
            {createMode === 'organization' ? 'Organization name' : 'Full name'}
            <input
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          {createMode === 'contact' && (
            <>
              <label>
                Organization
                <select
                  value={organizationId}
                  onChange={(event) => setOrganizationId(event.target.value)}
                >
                  <option value="">None</option>
                  {organizations.map((item) => (
                    <option value={item.id} key={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Job title
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
            {saving ? 'Creating…' : 'Create'}
          </button>
        </form>
      </section>
      <section className="workflow-panel">
        <div className="crm-panel-heading">
          <div>
            <h2>Sales pipeline</h2>
            <p>Move opportunities between governed stages.</p>
          </div>
          <form onSubmit={createPipeline}>
            <label>
              New pipeline
              <input
                required
                value={pipelineName}
                onChange={(event) => setPipelineName(event.target.value)}
              />
            </label>
            <button className="secondary-button" disabled={saving}>
              Create pipeline
            </button>
          </form>
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
                        <label>
                          Stage
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
                      </article>
                    ))}
                </section>
              ))}
            </div>
          ))
        ) : (
          <p className="empty-state">
            No pipeline configured. Create one through Kiko or the CRM API.
          </p>
        )}
      </section>
      <section className="workflow-panel crm-import-panel">
        <div>
          <h2>Data portability</h2>
          <p>
            Import up to 1,000 CSV rows after validation, or export sanitized
            tenant data.
          </p>
        </div>
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
        <div className="button-row">
          <button
            className="secondary-button"
            type="button"
            disabled={!importFile || saving}
            onClick={() => void previewImport()}
          >
            Preview import
          </button>
          <button
            className="primary-button"
            type="button"
            disabled={
              !importPreview || importPreview.invalid_rows > 0 || saving
            }
            onClick={() => void confirmImport()}
          >
            Confirm import
          </button>
          <button
            className="text-button"
            type="button"
            onClick={() => void downloadCrmExport('organizations')}
          >
            Export organizations
          </button>
          <button
            className="text-button"
            type="button"
            onClick={() => void downloadCrmExport('contacts')}
          >
            Export contacts
          </button>
        </div>
        {importPreview && (
          <div className="import-summary" role="status">
            <strong>{importPreview.valid_rows} valid rows</strong>
            <span>{importPreview.invalid_rows} rows need attention</span>
            {importPreview.rows
              .filter((row) => !row.valid)
              .map((row) => (
                <p key={row.row}>
                  Row {row.row}: {row.errors.join(', ')}
                </p>
              ))}
          </div>
        )}
      </section>
      <section className="workflow-panel">
        <h2>Clients</h2>
        <div className="agent-grid">
          {clients.map((client) => (
            <Link
              className="agent-card agent-card--link"
              href={'/dashboard/crm/clients/' + client.id}
              key={client.id}
            >
              <p className="eyebrow">{client.lifecycle_status}</p>
              <h3>{client.organization.name}</h3>
              <p>{client.industry || 'No industry'}</p>
            </Link>
          ))}
        </div>
        {clients.length === 0 && (
          <p className="empty-state">No client profiles found.</p>
        )}
      </section>
      <section className="workflow-panel">
        <h2>Organizations</h2>
        <div className="agent-grid">
          {organizations.map((organization) => (
            <Link
              className="agent-card agent-card--link"
              href={'/dashboard/crm/organizations/' + organization.id}
              key={organization.id}
            >
              <p className="eyebrow">{organization.status}</p>
              <h3>{organization.name}</h3>
              <p>
                {organization.member_count} contacts ·{' '}
                {organization.tags.join(', ') || 'No tags'}
              </p>
            </Link>
          ))}
        </div>
        {organizations.length === 0 && (
          <p className="empty-state">No organizations found.</p>
        )}
      </section>
      <section className="workflow-panel">
        <h2>Contacts</h2>
        <div className="agent-grid">
          {contacts.map((contact) => (
            <Link
              className="agent-card agent-card--link"
              href={'/dashboard/crm/contacts/' + contact.id}
              key={contact.id}
            >
              <p className="eyebrow">{contact.status}</p>
              <h3>{contact.full_name}</h3>
              <p>{contact.job_title || 'No job title'}</p>
              <p>
                {contact.methods.find((method) => method.is_primary)?.value ||
                  'No primary contact method'}
              </p>
            </Link>
          ))}
        </div>
        {contacts.length === 0 && (
          <p className="empty-state">No contacts found.</p>
        )}
      </section>
    </main>
  );
}
