"""Create a local-only test login without publishing a shared password."""

import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from argon2 import PasswordHasher

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    from app.config import get_settings
    from app.store import make_store

    settings = get_settings()
    if (
        settings.app_env != "development"
        or settings.database_mode != "sqlite"
        or settings.frontend_origin
        not in ("http://localhost:3000", "http://127.0.0.1:3000")
    ):
        raise SystemExit("Test account setup is only available in local development.")

    email = "test@avrt.local"
    store = make_store(settings)
    try:
        credentials = Path(settings.sqlite_path).parent / "test-login.txt"
        existing = store.find("users", email=email)
        if existing and credentials.is_file():
            print(f"Test account already exists: {email}. Credentials: {credentials}")
            return
        password = secrets.token_urlsafe(15)
        if existing:
            user = existing[0]
            user["password_hash"] = PasswordHasher().hash(password)
            store.put("users", user)
            action = "Reset"
        else:
            store.add_user(
                {
                    "id": uuid4().hex,
                    "email": email,
                    "password_hash": PasswordHasher().hash(password),
                    "role": "user",
                    "credits": 0,
                    "created_at": datetime.now(UTC),
                    "consent_history": True,
                    "consent_cloud": False,
                }
            )
            action = "Created"
        credentials.write_text(
            f"Local AVRT test login\nEmail: {email}\nPassword: {password}\n",
            encoding="utf-8",
        )
        print(f"{action} test account. Credentials: {credentials}")
    finally:
        store.close()


if __name__ == "__main__":
    main()
