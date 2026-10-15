"""Create the first admin user in an existing (real-data) database.

Usage:
    python -m app.bootstrap_admin --email ops@company.com --full-name "Ops Lead" --password '...'

Requires the password to be provided explicitly or via CAPACITY_BOOTSTRAP_PASSWORD.
Never prints or logs the password. Roles are seeded if absent (roles are
configuration, not demo data).
"""
from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.domain import Role, User

ROLES = {
    "Admin": "Full administrative access",
    "Infrastructure Planner": "Forecast, scenario, procurement, alert, and reporting operations",
    "Analyst": "Analysis, forecast, scenario, and reporting access",
    "Viewer": "Read-only dashboard access",
}


def bootstrap_admin(email: str, full_name: str, password: str, role: str = "Admin") -> int:
    db = SessionLocal()
    try:
        roles: dict[str, Role] = {}
        for name, description in ROLES.items():
            obj = db.scalar(select(Role).where(Role.name == name))
            if obj is None:
                obj = Role(name=name, description=description)
                db.add(obj)
                db.flush()
            roles[name] = obj
        if role not in roles:
            raise ValueError(f"Unknown role: {role}")
        normalized = email.strip().lower()
        existing = db.scalar(select(User).where(User.email == normalized))
        if existing is not None:
            print(f"User {normalized} already exists (id={existing.id}); nothing to do.")
            return existing.id
        user = User(email=normalized, full_name=full_name, password_hash=hash_password(password), roles=[roles[role]])
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Bootstrap admin created: {normalized} (id={user.id}, role={role})")
        return user.id
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first admin user (real-data mode).")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--password")
    parser.add_argument("--role", default="Admin", choices=sorted(ROLES))
    args = parser.parse_args()
    password = args.password or os.environ.get("CAPACITY_BOOTSTRAP_PASSWORD")
    if not password:
        print("Error: provide --password or set CAPACITY_BOOTSTRAP_PASSWORD", file=sys.stderr)
        raise SystemExit(2)
    if len(password) < 8:
        print("Error: password must be at least 8 characters", file=sys.stderr)
        raise SystemExit(2)
    bootstrap_admin(args.email, args.full_name, password, args.role)


if __name__ == "__main__":
    main()
