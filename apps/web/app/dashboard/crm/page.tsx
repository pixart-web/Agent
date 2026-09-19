'use client';

import type { CrmContact, CrmOrganization } from '@agent/shared';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  listCrmOrganizations,
  searchCrmContacts,
} from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function CrmPage() {
  const { user, loading } = useAuthenticatedUser();
  const [query, setQuery] = useState('');
  const [contacts, setContacts] = useState<CrmContact[]>([]);
  const [organizations, setOrganizations] = useState<CrmOrganization[]>([]);
  const [error, setError] = useState('');

  function refresh(search = '') {
    setError('');
    return Promise.all([
      searchCrmContacts(search),
      listCrmOrganizations(search),
    ])
      .then(([contactResult, organizationResult]) => {
        setContacts(contactResult.contacts);
        setOrganizations(organizationResult.organizations);
      })
      .catch(() => setError('Unable to load CRM records.'));
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
