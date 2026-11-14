import Image from 'next/image';
import Link from 'next/link';

const capabilities = [
  [
    'Kiko AI',
    'Turns a business request into a governed plan, assigned work and persisted results.',
  ],
  [
    'Execution control',
    'Routes sensitive actions through approvals, exact payload review and an immutable audit trail.',
  ],
  [
    'Business context',
    'Connects CRM, projects, marketing, automations and approved knowledge inside one workspace.',
  ],
  [
    'Operational evidence',
    'Shows real command, agent, tool and automation activity without invented business metrics.',
  ],
];

const agents = ['Supervisor', 'Sales', 'Marketing', 'Support', 'Development'];

export default function Home() {
  return (
    <main className="landing">
      <nav className="landing-nav" aria-label="Public navigation">
        <Link className="landing-brand" href="/">
          Kiko
        </Link>
        <div className="landing-nav__links">
          <a href="#capabilities">Capabilities</a>
          <a href="#governance">Governance</a>
          <a href="#plans">Plans</a>
        </div>
        <div className="landing-nav__actions">
          <Link href="/login">Log in</Link>
          <Link
            className="landing-button landing-button--small"
            href="/register"
          >
            Start trial
          </Link>
        </div>
      </nav>
      <section className="landing-hero">
        <div className="landing-hero__copy">
          <p className="landing-kicker">AI business operations</p>
          <h1>Turn intent into governed work.</h1>
          <p>
            Kiko coordinates agents, business context and approvals so teams can
            move from request to accountable execution.
          </p>
          <div className="landing-actions">
            <Link className="landing-button" href="/register">
              Start trial
            </Link>
            <a className="landing-text-link" href="#how-it-works">
              See how it works
            </a>
          </div>
        </div>
        <Image
          className="landing-hero__image"
          src="/images/kiko-orchestration-hero.png"
          width={1536}
          height={1024}
          priority
          alt="Abstract network of structured operational flows converging on one orchestration layer"
        />
      </section>
      <section
        className="landing-proof"
        aria-label="Available product areas"
        tabIndex={0}
      >
        {[
          'Commands',
          'Approvals',
          'CRM',
          'Automations',
          'Knowledge',
          'Analytics',
        ].map((item) => (
          <span key={item}>{item}</span>
        ))}
      </section>
      <section className="landing-section" id="capabilities">
        <h2>One operating layer for coordinated work.</h2>
        <div className="landing-capabilities">
          {capabilities.map(([title, description], index) => (
            <article
              className={
                index === 0 || index === 3
                  ? 'landing-capability landing-capability--tint'
                  : 'landing-capability'
              }
              key={title}
            >
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="landing-section landing-process" id="how-it-works">
        <div>
          <h2>A request becomes visible work.</h2>
          <p>
            Kiko keeps the plan, decisions, external actions and outcomes
            connected to the original business intent.
          </p>
        </div>
        <ol>
          <li>
            <strong>Describe the outcome</strong>
            <span>
              Use natural language inside a persistent workspace conversation.
            </span>
          </li>
          <li>
            <strong>Review the plan</strong>
            <span>
              The Supervisor decomposes work and assigns the right specialist
              agents.
            </span>
          </li>
          <li>
            <strong>Govern the action</strong>
            <span>
              Risk policy and approvals control external writes before
              execution.
            </span>
          </li>
          <li>
            <strong>Inspect the evidence</strong>
            <span>
              Results, failures and audit history remain available after
              execution.
            </span>
          </li>
        </ol>
      </section>
      <section className="landing-section landing-governance" id="governance">
        <div className="landing-governance__statement">
          <p className="landing-kicker">Built for accountable AI</p>
          <h2>Control stays with your team.</h2>
          <p>
            Workspace roles, tenant boundaries, approval fingerprints, provider
            allowlists and audit records are enforced by the application.
          </p>
        </div>
        <div className="landing-agent-list">
          <h3>Coordinated specialist agents</h3>
          {agents.map((agent) => (
            <span key={agent}>{agent}</span>
          ))}
        </div>
      </section>
      <section className="landing-section landing-plans" id="plans">
        <h2>Plans that match operating scale.</h2>
        <p>
          Final commercial pricing is confirmed with the product owner.
          Entitlements are already enforced by workspace.
        </p>
        <div className="landing-plan-grid">
          <article>
            <h3>Trial</h3>
            <p>
              Time-limited evaluation for a small team with governed core
              capabilities.
            </p>
            <Link href="/register">Start trial</Link>
          </article>
          <article>
            <h3>Business</h3>
            <p>
              Expanded usage, automations, integrations, storage and operational
              support.
            </p>
            <a href="mailto:hello@pixart.pt?subject=Kiko%20Business">
              Contact sales
            </a>
          </article>
          <article>
            <h3>Enterprise</h3>
            <p>
              Configurable scale, retention, support and platform administration
              controls.
            </p>
            <a href="mailto:hello@pixart.pt?subject=Kiko%20Enterprise">
              Contact sales
            </a>
          </article>
        </div>
      </section>
      <section className="landing-final">
        <h2>Make AI work accountable.</h2>
        <p>Start with a real workspace and a server-enforced 14-day trial.</p>
        <Link className="landing-button" href="/register">
          Start trial
        </Link>
      </section>
      <footer className="landing-footer">
        <strong>Kiko by Pixart</strong>
        <span>AI operating system for governed business work.</span>
        <div>
          <Link href="/login">Log in</Link>
          <Link href="/register">Register</Link>
        </div>
      </footer>
    </main>
  );
}
