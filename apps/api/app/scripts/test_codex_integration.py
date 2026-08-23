import argparse
import shutil
import subprocess

from app.core.config import get_settings
from app.integrations.codex.policy import CodexRepositoryPolicy
from app.integrations.codex.runner import PROFILES


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the Codex runner configuration safely")
    parser.add_argument(
        "--verify-binary",
        action="store_true",
        help="Run only `codex --version`; no repository clone, model call, commit, or push",
    )
    args = parser.parse_args()
    settings = get_settings()
    if not settings.codex_allowed_repository_list:
        raise SystemExit("CODEX_ALLOWED_REPOSITORIES must contain a repository")
    repository = settings.codex_allowed_repository_list[0]
    policy = CodexRepositoryPolicy(
        settings.codex_allowed_repository_list,
        settings.github_protected_branch_list,
        settings.github_allowed_branch_prefix_list,
    )
    repository = policy.authorize_repository(repository)
    profile = PROFILES.get(repository.casefold())
    if profile is None:
        raise SystemExit("The allowlisted repository has no fixed development profile")
    binary = shutil.which(settings.codex_binary)
    if args.verify_binary:
        if binary is None:
            raise SystemExit("Configured Codex binary was not found")
        subprocess.run(
            [binary, "--version"],
            check=True,
            shell=False,
            timeout=30,
        )
    print(
        {
            "repository": repository,
            "runner": settings.codex_runner,
            "binary_found": binary is not None,
            "validation_commands": [" ".join(command) for command in profile.validation_commands],
            "mode": "dry-run",
            "clone": False,
            "model_call": False,
            "commit": False,
            "push": False,
        }
    )


if __name__ == "__main__":
    main()
