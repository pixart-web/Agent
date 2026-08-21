from app.agents.prompts.development_v3 import PROMPT_VERSION, SYSTEM_PROMPT
from app.agents.specialists.common import PromptSpecializedAgent

AGENT = PromptSpecializedAgent(
    agent_id="development",
    name="Development",
    description="Inspects repositories and delegates governed development work to Codex.",
    prompt_version=PROMPT_VERSION,
    system_prompt=SYSTEM_PROMPT,
    allowed_tools=frozenset(
        {
            "internal.echo",
            "internal.summarize",
            "internal.create_note",
            "internal.simulate_external_action",
            "internal.simulate_critical_action",
            "github.get_repository",
            "github.list_branches",
            "github.read_file",
            "github.list_pull_requests",
            "github.get_pull_request",
            "github.list_issues",
            "github.get_issue",
            "github.create_issue",
            "github.comment_issue",
            "github.create_branch",
            "github.create_or_update_file",
            "github.open_pull_request",
            "codex.implement_task",
            "codex.review_pull_request",
            "codex.fix_pull_request",
        }
    ),
)
