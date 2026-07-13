import argparse
import json
import sys
import uuid
from pathlib import Path

from sqlmodel import Session

from app.core.db import engine
from app.modules.inventory.importer import import_workbooks


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the one-time inventory history import")
    parser.add_argument("--actor-user-id", required=True, type=uuid.UUID)
    parser.add_argument("--raw-workbook", required=True, type=Path)
    parser.add_argument("--finished-workbook", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    with Session(engine) as session:
        report = import_workbooks(
            session=session,
            actor_user_id=args.actor_user_id,
            raw_workbook=args.raw_workbook,
            finished_workbook=args.finished_workbook,
            dry_run=args.dry_run,
        )
    sys.stdout.write(f"{json.dumps(report, ensure_ascii=False)}\n")


if __name__ == "__main__":
    main()
