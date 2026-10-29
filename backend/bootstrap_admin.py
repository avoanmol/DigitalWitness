"""Create the first administrator interactively for a trusted local install."""

from __future__ import annotations

import argparse
import getpass

from dotenv import load_dotenv
from sqlalchemy import select

from backend.auth import hash_password
from backend.audit import append_audit_event
from backend.database import SessionLocal
from backend.models import User


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email")
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    email = args.email.strip().lower()
    name = args.name.strip()
    if not name:
        parser.error("--name cannot be empty")
    password = getpass.getpass("Choose an administrator password (12+ characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if len(password) < 12 or len(password) > 128:
        parser.error("Password must contain 12 to 128 characters")
    if password != confirmation:
        parser.error("Passwords do not match")

    with SessionLocal() as db:
        existing_admin = db.scalar(select(User).where(User.role == "admin", User.is_active.is_(True)).limit(1))
        if existing_admin:
            raise SystemExit("An active administrator already exists; use the admin user-management screen.")
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, full_name=name, password_hash=hash_password(password), role="admin", is_active=True)
            db.add(user)
        else:
            user.full_name = name
            user.password_hash = hash_password(password)
            user.role = "admin"
            user.is_active = True
        db.flush()
        append_audit_event(db, action="admin.bootstrap", target_type="user",
                           actor_id=user.id, actor_role="admin", target_id=str(user.id),
                           details={"method": "interactive_cli"})
        db.commit()
    print(f"Active administrator ready: {email}")


if __name__ == "__main__":
    main()
