import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.integrations.codex.errors import CodexWorkspaceError


@dataclass(frozen=True)
class CodexWorkspace:
    root: Path
    repository: Path
    metadata: Path


class CodexWorkspaceManager:
    def __init__(self, workspace_root: str) -> None:
        self.workspace_root = Path(workspace_root).expanduser().resolve()

    def create(self, run_id: UUID) -> CodexWorkspace:
        root = (self.workspace_root / str(run_id)).resolve()
        if root.parent != self.workspace_root:
            raise CodexWorkspaceError("Invalid Codex workspace path")
        if root.exists():
            raise CodexWorkspaceError("Codex workspace already exists")
        repository = root / "repository"
        metadata = root / "metadata"
        metadata.mkdir(parents=True, exist_ok=False)
        return CodexWorkspace(root=root, repository=repository, metadata=metadata)

    def cleanup(self, workspace: CodexWorkspace) -> None:
        root = workspace.root.resolve()
        if root.parent != self.workspace_root or not root.exists():
            return
        shutil.rmtree(root)
