from app.schemas.agent import Agent

_AGENTS = [
    Agent(
        id="supervisor",
        name="Supervisor",
        description="Coordinates priorities, delegates work, and tracks execution.",
    ),
    Agent(
        id="marketing",
        name="Marketing",
        description="Supports campaigns, content operations, and brand workflows.",
    ),
    Agent(
        id="sales",
        name="Sales",
        description="Assists pipeline management, proposals, and commercial follow-up.",
    ),
    Agent(
        id="support",
        name="Support",
        description="Helps resolve customer requests and organize service knowledge.",
    ),
    Agent(
        id="development",
        name="Development",
        description="Supports engineering delivery, quality, and technical operations.",
    ),
]


def list_agents() -> list[Agent]:
    return _AGENTS.copy()
