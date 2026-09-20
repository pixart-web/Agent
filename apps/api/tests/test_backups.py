import subprocess
from pathlib import Path

import pytest

from app.operations.backups import BackupError, create_backup, restore_backup

DATABASE_URL = "postgresql+psycopg://operator:secret-value@db.internal:5433/kiko"


def test_backup_uses_environment_for_password_and_writes_checksum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "kiko.dump"
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(command, *, check, env):
        assert check is True
        destination.write_bytes(b"synthetic backup")
        calls.append((command, env))

    monkeypatch.setattr(subprocess, "run", fake_run)
    checksum = create_backup(DATABASE_URL, destination)
    command, environment = calls[0]
    assert "secret-value" not in " ".join(command)
    assert environment["PGPASSWORD"] == "secret-value"
    assert environment["PGHOST"] == "db.internal"
    assert checksum.read_text(encoding="utf-8").endswith("  kiko.dump\n")


def test_restore_requires_exact_database_confirmation_and_valid_checksum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "kiko.dump"

    def fake_dump(command, *, check, env):
        destination.write_bytes(b"synthetic backup")

    monkeypatch.setattr(subprocess, "run", fake_dump)
    create_backup(DATABASE_URL, destination)
    with pytest.raises(BackupError, match="exactly match"):
        restore_backup(DATABASE_URL, destination, confirm_database="wrong")

    calls: list[list[str]] = []

    def fake_restore(command, *, check, env):
        calls.append(command)

    monkeypatch.setattr(subprocess, "run", fake_restore)
    restore_backup(DATABASE_URL, destination, confirm_database="kiko")
    assert calls[0][0] == "pg_restore"
    assert "--exit-on-error" in calls[0]


def test_restore_rejects_tampered_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = tmp_path / "kiko.dump"

    def fake_dump(command, *, check, env):
        destination.write_bytes(b"synthetic backup")

    monkeypatch.setattr(subprocess, "run", fake_dump)
    create_backup(DATABASE_URL, destination)
    destination.write_bytes(b"tampered")
    with pytest.raises(BackupError, match="checksum"):
        restore_backup(DATABASE_URL, destination, confirm_database="kiko")
