export const AGENT_CATALOG = [
  {
    id: 'supervisor',
    name: 'Supervisor',
    description:
      'Coordinates priorities, delegates work, and tracks execution.',
  },
  {
    id: 'marketing',
    name: 'Marketing',
    description: 'Supports campaigns, content operations, and brand workflows.',
  },
  {
    id: 'sales',
    name: 'Sales',
    description:
      'Assists pipeline management, proposals, and commercial follow-up.',
  },
  {
    id: 'support',
    name: 'Support',
    description:
      'Helps resolve customer requests and organize service knowledge.',
  },
  {
    id: 'development',
    name: 'Development',
    description:
      'Supports engineering delivery, quality, and technical operations.',
  },
] as const;

export type AgentId = (typeof AGENT_CATALOG)[number]['id'];
