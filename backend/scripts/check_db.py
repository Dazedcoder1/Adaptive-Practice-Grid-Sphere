"""Verify the database connection. Run from backend/: python -m scripts.check_db"""

import sys

from sqlalchemy import text

from app.config.database import engine


def main() -> int:
    try:
        with engine.connect() as c:
            version = c.execute(text("select version()")).scalar_one()
        print("✓ connected:", version.split(",")[0])
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"✗ database check failed: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
