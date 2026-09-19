from app.agents.prompts.support_v3 import PROMPT_VERSION, SYSTEM_PROMPT
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
            "calendar.list_calendars",
            "calendar.list_events",
            "calendar.search_events",
            "calendar.get_event",
            "calendar.get_availability",
            "calendar.create_event",
            "calendar.update_event",
            "calendar.cancel_event",
            "email.list_messages",
            "email.get_message",
            "email.get_thread",
            "email.search",
            "email.reply",
            "email.mark_read",
        }
    ),
)
