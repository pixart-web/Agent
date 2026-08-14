from app.ai.prompts.supervisor_plan_v1 import (
    AvailableAgent,
    build_system_prompt,
    build_user_prompt,
)
from app.ai.provider_factory import get_llm_provider
from app.core.config import get_settings
from app.schemas.supervisor import SupervisorPlanProposal


def main() -> None:
    settings = get_settings()
    if not settings.openai_api_key:
        print("Skipped: OPENAI_API_KEY is not configured.")
        return

    agents = [
        AvailableAgent(
            id="marketing",
            name="Marketing",
            description="Campaign and content operations",
        ),
        AvailableAgent(
            id="sales",
            name="Sales",
            description="Lead and commercial operations",
        ),
    ]
    provider = get_llm_provider()
    result = provider.generate_structured(
        system_prompt=build_system_prompt(agents, max_tasks=3),
        user_prompt=build_user_prompt("Prepare a short internal campaign plan."),
        response_model=SupervisorPlanProposal,
    )
    print(
        {
            "validated": True,
            "provider": result.provider,
            "model": result.model,
            "tasks": len(result.data.tasks),
            "total_tokens": result.total_tokens,
            "latency_ms": result.latency_ms,
            "request_id": result.request_id,
        }
    )


if __name__ == "__main__":
    main()
