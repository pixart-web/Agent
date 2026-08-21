from app.core.config import get_settings
from app.integrations.credentials import EnvironmentCredentialProvider
from app.integrations.github.client import build_github_client
from app.integrations.github.policy import RepositoryAccessPolicy


def main() -> None:
    settings = get_settings()
    credentials = EnvironmentCredentialProvider(settings)
    if not settings.github_integration_enabled:
        raise SystemExit("GITHUB_INTEGRATION_ENABLED must be true")
    if not credentials.configured("github"):
        raise SystemExit("GITHUB_TOKEN must be configured")
    if not settings.github_allowed_repository_list:
        raise SystemExit("GITHUB_ALLOWED_REPOSITORIES must contain a repository")

    repository = settings.github_allowed_repository_list[0]
    policy = RepositoryAccessPolicy(
        settings.github_allowed_repository_list,
        settings.github_protected_branch_list,
        settings.github_allowed_branch_prefix_list,
    )
    repository = policy.authorize(repository, "get_repository")
    credential = credentials.resolve("github")
    client = build_github_client(credential.access_token, settings.github_api_timeout_seconds)

    try:
        metadata = client.get_repository(repository)
        branches = client.list_branches(repository, 20)
        print(
            {
                "repository": metadata["full_name"],
                "default_branch": metadata["default_branch"],
                "branches": [branch["name"] for branch in branches],
                "mode": "read-only",
            }
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
