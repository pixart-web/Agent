from app.agents.prompts.sales_v2 import PROMPT_VERSION, SYSTEM_PROMPT
from app.agents.specialists.common import PromptSpecializedAgent

AGENT = PromptSpecializedAgent(
    agent_id="sales",
    name="Sales",
    description="Prepares ethical outreach, proposals and follow-up actions.",
    prompt_version=PROMPT_VERSION,
    system_prompt=SYSTEM_PROMPT,
    allowed_tools=frozenset(
        {
            "internal.echo",
            "internal.summarize",
            "internal.create_note",
            "internal.simulate_external_action",
            "email.search",
            "email.get_message",
            "email.get_thread",
            "email.send",
            "email.reply",
        }
    ),
)
