"""Offline administrative action; never grant admin by public signup."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import get_settings
from app.store import make_store

parser = argparse.ArgumentParser()
parser.add_argument("email")
args = parser.parse_args()
settings = get_settings()
if settings.database_mode != "mongo":
    raise SystemExit("Run against the persistent MongoDB store.")
store = make_store(settings)
users = store.find("users", email=args.email.lower())
if not users:
    raise SystemExit("Account not found. Register first.")
user = users[0]
user["role"] = "admin"
store.put("users", user)
print("Admin role granted to the selected account.")
