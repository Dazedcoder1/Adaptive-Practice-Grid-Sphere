"""Create a Super Admin account (there is no public admin sign-up).

    python -m scripts.create_superadmin --email you@example.com

You'll be prompted for the password; it isn't echoed or stored in shell history.
"""

import argparse
import getpass
import sys

from app.config.database import SessionLocal, transaction
from app.modules.identity.schemas import _password_rules
from app.modules.identity.service import create_super_admin
from app.shared.exceptions import AppError


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    args = ap.parse_args()

    pw = getpass.getpass("Password (min 10 chars, letters + numbers): ")
    if len(pw) < 10:
        print("✗ Password must be at least 10 characters.")
        return 1
    try:
        _password_rules(pw)
    except ValueError as e:
        print(f"✗ {e}")
        return 1
    if getpass.getpass("Confirm password: ") != pw:
        print("✗ Passwords don't match.")
        return 1

    with SessionLocal() as db:
        try:
            with transaction(db):
                user = create_super_admin(db, args.email, pw)
        except AppError as e:
            print(f"✗ {e.message}")
            return 1
    print(f"✓ Super Admin created: {user.email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
