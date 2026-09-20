import argparse
import os
from pathlib import Path

from app.operations.backups import create_backup


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a checksummed PostgreSQL custom backup")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    checksum = create_backup(database_url, args.destination)
    print(f"Backup created; checksum: {checksum}")


if __name__ == "__main__":
    main()
