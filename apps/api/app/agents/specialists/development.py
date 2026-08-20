from app.agents.prompts.development_v1 import PROMPT_VERSION, SYSTEM_PROMPT
from app.agents.specialists.common import PromptSpecializedAgent

AGENT = PromptSpecializedAgent(
    agent_id="development",
    name="Development",
    description="Prepares technical specifications and simulated engineering actions.",
    prompt_version=PROMPT_VERSION,
    system_prompt=SYSTEM_PROMPT,
    allowed_tools=frozenset(
        {
            "internal.echo",
            "internal.summarize",
            "internal.create_note",
            "internal.simulate_external_action",
            "internal.simulate_critical_action",
        }
    ),
)
