"""Verify R2 credentials: upload, read back, delete.

Run from backend/: python -m scripts.check_r2"""

import sys
import time

from app.config.settings import settings
from app.integrations import storage


def main() -> int:
    if not settings.r2_configured:
        print(
            "✗ R2 not configured — fill R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / "
            "R2_SECRET_ACCESS_KEY / R2_BUCKET_NAME in .env"
        )
        return 1
    key = f"healthcheck/{int(time.time())}.txt"
    try:
        storage.upload(key, b"hello from adaptive-practice", "text/plain")
        print("✓ upload")
        body = storage.get_r2().get_object(Bucket=settings.r2_bucket_name, Key=key)["Body"].read()
        print("✓ download:", body.decode())
        storage.delete(key)
        print("✓ delete — R2 is configured correctly")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"✗ R2 check failed: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
