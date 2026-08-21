import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.integrations.codex.errors import (
    CodexRunnerUnavailableError,
    CodexTimeoutError,
    CodexValidationError,
)

ResultModel = TypeVar("ResultModel", bound=BaseModel)


@dataclass(frozen=True)
class CodexAdapterExecution:
    result: BaseModel
    exit_code: int


class CodexAdapter(Protocol):
    def execute(
        self,
        *,
        prompt: str,
        repository: Path,
        metadata: Path,
        output_schema: type[ResultModel],
        api_key: str,
        writable: bool,
        model: str | None,
    ) -> CodexAdapterExecution: ...


def safe_process_environment() -> dict[str, str]:
    allowed = {
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USERPROFILE",
        "WINDIR",
    }
    return {key: value for key, value in os.environ.items() if key.upper() in allowed}


class CodexCLIAdapter:
    def __init__(
        self,
        *,
        binary: str,
        timeout_seconds: int,
        max_output_chars: int,
    ) -> None:
        self.binary = binary
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars

    def execute(
        self,
        *,
        prompt: str,
        repository: Path,
        metadata: Path,
        output_schema: type[ResultModel],
        api_key: str,
        writable: bool,
        model: str | None,
    ) -> CodexAdapterExecution:
        schema_path = metadata / "output-schema.json"
        result_path = metadata / "result.json"
        log_path = metadata / "technical.log"
        schema_path.write_text(
            json.dumps(output_schema.model_json_schema(), separators=(",", ":")),
            encoding="utf-8",
        )
        args = [
            self.binary,
            "--cd",
            str(repository),
            "--ask-for-approval",
            "never",
            "-c",
            'shell_environment_policy.inherit="core"',
            "-c",
            "shell_environment_policy.ignore_default_excludes=false",
            "-c",
            'shell_environment_policy.exclude=["CODEX_API_KEY"]',
            "-c",
            "allow_login_shell=false",
            "exec",
            "-",
            "--ephemeral",
            "--ignore-user-config",
            "--sandbox",
            "workspace-write" if writable else "read-only",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(result_path),
        ]
        if model:
            args.extend(["--model", model])
        environment = safe_process_environment()
        environment["CODEX_API_KEY"] = api_key
        try:
            with log_path.open("w", encoding="utf-8") as technical_log:
                completed = subprocess.run(
                    args=args,
                    cwd=repository,
                    env=environment,
                    input=prompt,
                    text=True,
                    stdout=technical_log,
                    stderr=technical_log,
                    timeout=self.timeout_seconds,
                    check=False,
                    shell=False,
                )
        except FileNotFoundError as error:
            raise CodexRunnerUnavailableError("Codex CLI binary is not available") from error
        except subprocess.TimeoutExpired as error:
            raise CodexTimeoutError("Codex execution exceeded its timeout") from error
        except OSError as error:
            raise CodexRunnerUnavailableError("Codex CLI could not be started") from error
        finally:
            # Raw output can contain repository content or process diagnostics.
            log_path.unlink(missing_ok=True)
        if completed.returncode != 0:
            raise CodexValidationError("Codex CLI execution failed")
        if not result_path.is_file():
            raise CodexValidationError("Codex did not produce a structured result")
        with result_path.open("r", encoding="utf-8") as result_file:
            content = result_file.read(self.max_output_chars + 1)
        if len(content) > self.max_output_chars:
            raise CodexValidationError("Codex output exceeds the configured limit")
        if api_key and api_key in content:
            raise CodexValidationError("Codex output contained credential material")
        try:
            result = output_schema.model_validate_json(content)
        except Exception as error:
            raise CodexValidationError("Codex returned an invalid structured result") from error
        return CodexAdapterExecution(result=result, exit_code=completed.returncode)
