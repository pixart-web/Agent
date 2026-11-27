import Link from 'next/link';

import { KikoAvatar } from '../components/kiko/kiko-avatar';
import { KikoLogo } from '../components/kiko/kiko-logo';

const capabilities = [
  [
    'Pedidos que viram planos',
    'Escreves o que precisas em linguagem natural. O Supervisor divide o trabalho em tarefas e atribui cada uma ao agente certo.',
  ],
  [
    'Aprovação antes de agir',
    'Envios, alterações externas e ações sensíveis esperam por uma pessoa. Vês exatamente o que vai ser feito antes de aprovar.',
  ],
  [
    'O contexto do negócio num só sítio',
    'CRM, projetos, marketing, automatizações e conhecimento aprovado ficam no mesmo workspace, ao alcance dos agentes.',
  ],
  [
    'Histórico verificável',
    'Cada passo fica registado: quem pediu, que agente trabalhou, que ferramenta correu e com que resultado.',
  ],
];

const steps = [
  ['Descreve o resultado', 'Numa conversa que fica guardada no workspace.'],
  [
    'Revê o plano',
    'O Supervisor propõe tarefas, dependências e agentes; tu aprovas ou pedes outra versão.',
  ],
  [
    'Controla as ações',
    'A política de risco decide o que corre sozinho e o que precisa de aprovação.',
  ],
  [
    'Consulta a evidência',
    'Resultados, falhas e auditoria continuam disponíveis depois da execução.',
  ],
];

const agents = [
  ['Supervisor', 'planeia e coordena'],
  ['Vendas', 'propostas e seguimento comercial'],
  ['Marketing', 'campanhas e conteúdos'],
  ['Suporte', 'pedidos de clientes'],
  ['Desenvolvimento', 'trabalho técnico'],
];

const safeguards = [
  'IA local: os dados do negócio não saem para fornecedores externos de IA',
  'Funções por workspace: dono, administrador, gestor, membro e leitura',
  'Verificação em dois passos com app de autenticação',
  'App para macOS com a sessão guardada no Porta-chaves',
];

export default function Home() {
  return (
    <main className="landing">
      <nav className="landing-nav" aria-label="Navegação pública">
        <Link className="landing-brand" href="/" aria-label="Kiko — início">
          <KikoLogo width={150} />
        </Link>
        <div className="landing-nav__links">
          <a href="#capacidades">Capacidades</a>
          <a href="#como-funciona">Como funciona</a>
          <a href="#planos">Planos</a>
        </div>
        <div className="landing-nav__actions">
          <Link href="/login">Entrar</Link>
          <Link
            className="landing-button landing-button--small"
            href="/register"
          >
            Experimentar
          </Link>
        </div>
      </nav>

      <section className="landing-hero">
        <div className="landing-hero__copy">
          <p className="landing-kicker">Sistema operativo de IA da Pixart</p>
          <h1>Diz ao Kiko o que precisas. Ele organiza o trabalho.</h1>
          <p>
            O Kiko transforma pedidos em planos, coordena agentes especializados
            e pede a tua aprovação antes de qualquer ação sensível.
          </p>
          <div className="landing-actions">
            <Link className="landing-button" href="/register">
              Criar um workspace
            </Link>
            <a className="landing-text-link" href="#como-funciona">
              Ver como funciona
            </a>
          </div>
        </div>
        <div className="landing-stage" aria-hidden="true">
          <div className="landing-stage__orbit" />
          <KikoAvatar state="idle" size={260} />
          <div className="landing-chip landing-chip--plan">
            <span className="landing-chip__dot" />
            Plano com 3 tarefas
          </div>
          <div className="landing-chip landing-chip--approval">
            <span className="landing-chip__dot" />À espera de aprovação
          </div>
          <div className="landing-chip landing-chip--done">
            <span className="landing-chip__dot" />
            Proposta enviada ao cliente
          </div>
        </div>
      </section>

      <section className="landing-proof" aria-label="Áreas do produto">
        {[
          'Conversas',
          'Comandos',
          'Aprovações',
          'CRM',
          'Automatizações',
          'Conhecimento',
          'Relatórios',
        ].map((item) => (
          <span key={item}>{item}</span>
        ))}
      </section>

      <section className="landing-section" id="capacidades">
        <h2>Uma camada que liga pedidos, pessoas e agentes.</h2>
        <div className="landing-capabilities">
          {capabilities.map(([title, description]) => (
            <article className="landing-capability" key={title}>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section landing-process" id="como-funciona">
        <div>
          <h2>Um pedido torna-se trabalho visível.</h2>
          <p>
            O plano, as decisões, as ações externas e os resultados ficam
            ligados ao pedido original, do início ao fim.
          </p>
        </div>
        <ol>
          {steps.map(([title, text]) => (
            <li key={title}>
              <strong>{title}</strong>
              <span>{text}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="landing-section landing-governance">
        <div className="landing-governance__statement">
          <p className="landing-kicker">IA com responsabilidade</p>
          <h2>O controlo fica com a tua equipa.</h2>
          <ul className="landing-safeguards">
            {safeguards.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div className="landing-agent-list">
          <h3>Agentes especializados</h3>
          {agents.map(([name, role]) => (
            <span key={name}>
              <strong>{name}</strong>
              {role}
            </span>
          ))}
        </div>
      </section>

      <section className="landing-section landing-plans" id="planos">
        <h2>Planos à medida da operação.</h2>
        <p>
          Os preços finais são confirmados com a Pixart. Os limites de cada
          plano já são aplicados por workspace.
        </p>
        <div className="landing-plan-grid">
          <article>
            <h3>Experimental</h3>
            <p>
              14 dias para uma equipa pequena avaliar as capacidades principais.
            </p>
            <Link href="/register">Começar</Link>
          </article>
          <article>
            <h3>Business</h3>
            <p>
              Mais utilização, automatizações, integrações, armazenamento e
              suporte.
            </p>
            <a href="mailto:hello@pixart.pt?subject=Kiko%20Business">
              Falar com a Pixart
            </a>
          </article>
          <article>
            <h3>Enterprise</h3>
            <p>
              Escala, retenção, suporte e administração da plataforma à medida.
            </p>
            <a href="mailto:hello@pixart.pt?subject=Kiko%20Enterprise">
              Falar com a Pixart
            </a>
          </article>
        </div>
      </section>

      <section className="landing-final">
        <h2>Põe a IA a trabalhar com regras.</h2>
        <p>Cria um workspace e experimenta durante 14 dias.</p>
        <Link className="landing-button" href="/register">
          Criar um workspace
        </Link>
      </section>

      <footer className="landing-footer">
        <strong>Kiko by Pixart</strong>
        <span>Sistema operativo de IA para trabalho com regras.</span>
        <div>
          <Link href="/login">Entrar</Link>
          <Link href="/register">Criar conta</Link>
        </div>
      </footer>
    </main>
  );
}
