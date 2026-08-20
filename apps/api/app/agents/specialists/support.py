from app.agents.prompts.support_v1 import PROMPT_VERSION, SYSTEM_PROMPT
from app.agents.specialists.common import PromptSpecializedAgent

AGENT = PromptSpecializedAgent(
    agent_id="support",
    name="Support",
    description="Analyzes requests and prepares safe internal response actions.",
    prompt_version=PROMPT_VERSION,
    system_prompt=SYSTEM_PROMPT,
    allowed_tools=frozenset(
        {
            "internal.echo",
            "internal.summarize",
            "internal.create_note",
            "internal.simulate_external_action",
        }
    ),
)
