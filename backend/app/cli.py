import argparse
from uuid import uuid4
from datetime import datetime, timezone
from .config import get_settings
from .store import make_store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["promote"])
    parser.add_argument("email")
    args = parser.parse_args()
    settings = get_settings()
    if settings.database_mode != "mongo":
        raise SystemExit("Cần MongoDB để giữ quyền admin.")
    store = make_store(settings)
    users = store.find("users", email=args.email.lower())
    if not users:
        raise SystemExit("Đăng ký tài khoản trước.")
    user = users[0]
    user["role"] = "admin"
    store.put("users", user)
    store.put(
        "audit",
        {
            "id": uuid4().hex,
            "actor_id": user["id"],
            "action": "admin.promote.cli",
            "created_at": datetime.now(timezone.utc),
        },
    )
    print("Đã cấp quyền admin cho tài khoản được chọn.")


if __name__ == "__main__":
    main()
