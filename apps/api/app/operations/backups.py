import hashlib
import os
import subprocess
from hmac import compare_digest
from pathlib import Path

from sqlalchemy.engine import make_url


class BackupError(RuntimeError):
    pass


def postgres_environment(database_url: str) -> tuple[dict[str, str], str]:
    url = make_url(database_url)
    if not url.drivername.startswith("postgresql") or not url.database:
        raise BackupError("A PostgreSQL DATABASE_URL is required")
    environment = os.environ.copy()
    values = {
        "PGHOST": url.host,
        "PGPORT": str(url.port) if url.port else None,
        "PGUSER": url.username,
        "PGPASSWORD": url.password,
    }
    environment.update({key: value for key, value in values.items() if value is not None})
    return environment, url.database


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup(database_url: str, destination: Path) -> Path:
    destination = destination.resolve()
    if destination.exists():
        raise BackupError("Backup destination already exists")
    if not destination.parent.is_dir():
        raise BackupError("Backup destination directory does not exist")
    environment, database = postgres_environment(database_url)
    subprocess.run(
        [
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--file",
            str(destination),
            database,
        ],
        check=True,
        env=environment,
    )
    if not destination.is_file():
        raise BackupError("pg_dump did not create the backup")
    checksum = sha256_file(destination)
    checksum_path = destination.with_suffix(destination.suffix + ".sha256")
    checksum_path.write_text(f"{checksum}  {destination.name}\n", encoding="utf-8")
    checksum_path.chmod(0o600)
    return checksum_path


def restore_backup(
    database_url: str,
    backup: Path,
    *,
    confirm_database: str,
) -> None:
    backup = backup.resolve()
    if not backup.is_file():
        raise BackupError("Backup file does not exist")
    environment, database = postgres_environment(database_url)
    if confirm_database != database:
        raise BackupError("Restore confirmation must exactly match the target database")
    checksum_path = backup.with_suffix(backup.suffix + ".sha256")
    if not checksum_path.is_file():
        raise BackupError("Backup checksum file is missing")
    checksum_fields = checksum_path.read_text(encoding="utf-8").split()
    if not checksum_fields:
        raise BackupError("Backup checksum file is invalid")
    expected = checksum_fields[0]
    if not compare_digest(expected, sha256_file(backup)):
        raise BackupError("Backup checksum validation failed")
    subprocess.run(
        [
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "--exit-on-error",
            "--dbname",
            database,
            str(backup),
        ],
        check=True,
        env=environment,
    )
