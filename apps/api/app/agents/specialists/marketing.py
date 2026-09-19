from app.agents.prompts.marketing_v4 import PROMPT_VERSION, SYSTEM_PROMPT
from app.agents.specialists.common import PromptSpecializedAgent

AGENT = PromptSpecializedAgent(
    agent_id="marketing",
    name="Marketing",
    description="Creates briefs, content ideas and simulated campaign actions.",
    prompt_version=PROMPT_VERSION,
    system_prompt=SYSTEM_PROMPT,
    allowed_tools=frozenset(
        {
            "internal.echo",
            "internal.summarize",
            "internal.create_note",
            "internal.simulate_external_action",
            "crm.list_clients",
            "crm.get_client_360",
            "crm.list_projects",
            "crm.list_pipelines",
            "crm.list_opportunities",
            "crm.search_contacts",
            "crm.get_contact",
            "crm.get_organization",
            "crm.list_organizations",
            "crm.list_activities",
            "crm.create_organization",
            "crm.create_contact",
            "crm.update_contact",
            "crm.add_note",
            "crm.link_email",
            "crm.link_event",
            "calendar.list_calendars",
            "calendar.list_events",
            "calendar.search_events",
            "calendar.get_event",
            "calendar.get_availability",
            "calendar.create_event",
            "calendar.update_event",
            "calendar.cancel_event",
        }
    ),
)
