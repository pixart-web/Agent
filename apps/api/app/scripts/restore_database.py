import argparse
import os
from pathlib import Path

from app.operations.backups import restore_backup


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore a checksummed PostgreSQL backup")
    parser.add_argument("backup", type=Path)
    parser.add_argument("--confirm-database", required=True)
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    restore_backup(database_url, args.backup, confirm_database=args.confirm_database)
    print("Restore completed")


if __name__ == "__main__":
    main()
