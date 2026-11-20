# Kiko Alive — UX specification

Language of the new shell and home: European Portuguese (the module screens keep their
current wording until they are translated).

## Application shell

Every dashboard page renders `DashboardNav` (the Kiko Alive shell) first inside `<main>`.

**Navigation rail (left).** Kiko brand with the live character; primary sections: Início,
Conversas, Comandos, Projetos, Tarefas, Agentes, Automatizações, CRM, Conhecimento,
Relatórios. "Mais módulos" (a disclosure, open automatically when one of its pages is
current) holds Aprovações, Execuções, Notificações, Email, Calendário, Marketing,
Integrações, Codex, Subscrição and, for platform admins, Administração. The footer holds the
workspace (with a selector when the account belongs to several workspaces, which switches
the active workspace and reloads), Definições, the user and "Terminar sessão".

- Collapsible to icons (choice remembered per browser); tooltips via `title`.
- Active page: `aria-current="page"` and an amber→violet fill.
- Below 1000 px wide the rail is icons-only; below 720 px it is hidden behind a menu button
  in the top bar and opens as an overlay with a scrim.

**Top bar.** Search ("Pesquisar no Kiko…", ⌘K) opens the command palette; on pages other
than home, an activity button with a badge (pending approvals + unread alerts) opens the
context panel as a drawer.

**Context panel.** Approvals waiting (only when there are any), executions in progress with
real plan progress, the specialist agents and what each is doing, recent activity
(notifications and tool executions). Docked on the right of the home screen (stacked below
the main column under 1240 px); a closable drawer elsewhere (Escape closes it).

**Read-only members** see a notice under the top bar and no request box on the home screen.

## Home

1. Greeting by time of day with the first name and the date.
2. **Hero:** "Olá, eu sou o Kiko." with the character, a one-line purpose and the live
   status (label + explanation).
3. **Local AI notice** when the runtime or model is unavailable, with the recovery hint.
4. **Request box:** "O que queres que eu faça hoje?". Enter sends, Shift+Enter adds a line.
   Sending starts a Kiko conversation (the existing conversation workflow) and opens it.
   States: listening (focused), thinking (sending), success/error (shown for 4 s), disabled
   when offline or read-only. "Continuar" links reopen the last three conversations.
   No microphone or attachment controls: neither is implemented.
5. **Quick actions:** Criar um plano (new command), Executar uma tarefa (tasks), Analisar
   resultados (reports), Automatizar um processo (automations).
6. **Ecosystem:** Email, Calendário, GitHub and Codex with the state each integration
   reports (Ligado, Por ligar, Desativado, Sem credenciais…); only connected ones are
   highlighted. Integrations the product does not have are not shown.
7. **Context panel** (docked).

## Character

`KikoAvatar` states and what drives them (`lib/kiko-state.ts`, highest priority first):

| State                 | Shown when                                              | Expression                         |
| --------------------- | ------------------------------------------------------- | ---------------------------------- |
| Sem ligação (offline) | The API health check fails                              | Dimmed, flat eyes, lights off      |
| A pensar (thinking)   | A request from this screen is waiting for the API       | Three pulsing dots                 |
| Precisa de atenção    | The last request failed, or the local AI is unavailable | Worried brows, red accents         |
| Feito (success)       | The last request succeeded (4 s)                        | Smile, two small hops              |
| A ouvir (listening)   | The request box has focus                               | Round eyes, head tilt              |
| A executar            | Agent runs are active in the workspace                  | Spinning amber ring, glowing core  |
| À espera de aprovação | Actions wait for approval                               | Round eyes, pulsing amber ring     |
| A planear             | Commands are in planning                                | Glancing eyes, dotted violet ring  |
| Em repouso (sleeping) | No interaction for 5 minutes and nothing above applies  | Dimmed, slow float                 |
| Disponível (idle)     | Otherwise                                               | Happy eyes, gentle float and blink |

The workspace signals refresh every 20 s (only while the page is visible). The state is
always also written as text in a `role="status"` live region.

## Adaptive workspaces

`KikoWorkspaceMode` heads the work screens with the mode, Kiko's state, a sentence from real
data and, for commands, the steps Pedido → Plano → Aprovação → Execução → Resultado:

- **Command — planning:** no plan (generate or create one), Supervisor planning in the
  background (planning), draft plan ready (waiting for approval).
- **Command — execution:** tasks completed / total, running, waiting for approval; completed
  (success), failed (error), cancelled.
- **Conversation:** thinking while a message is sent; planning while a Supervisor run is
  active; approvals waiting; an operation error.
- **Analysis (Relatórios):** the period and the source (stored records).

The existing panels under the header (plan review, agent analysis, execution engine,
approvals, activity timeline) are unchanged.

## Accessibility

Skip link; landmarks (`nav` "Navegação principal", `main`, `aside` "Atividade do
workspace"); visible focus; every icon-only control has an `aria-label`; the drawer takes
focus when opened; reduced motion honoured; status in text. Verified with axe (WCAG 2 A/AA,
serious and critical) on every dashboard route at desktop and phone width.
