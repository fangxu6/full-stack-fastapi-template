import argparse
import json
import sys

from sqlmodel import Session

from app.core.audit import provision_system_actor
from app.core.db import engine


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create or retrieve a non-interactive audit System Actor"
    )
    parser.add_argument("--actor-key", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()

    with Session(engine) as session:
        actor = provision_system_actor(
            session=session,
            actor_key=args.actor_key,
            email=args.email,
        )
        session.commit()
        output = {
            "id": str(actor.id),
            "actor_key": actor.system_actor_key,
            "email": actor.email,
        }

    sys.stdout.write(f"{json.dumps(output)}\n")


if __name__ == "__main__":
    main()
