"""Mongo, local SQLite, and nonpersistent test stores."""

import copy
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError


class MemoryStore:
    def __init__(self):
        self.data = {}
        self.lock = threading.RLock()

    def put(self, collection, doc):
        with self.lock:
            self.data.setdefault(collection, {})[doc["id"]] = copy.deepcopy(doc)
        return doc

    def get(self, collection, key):
        with self.lock:
            return copy.deepcopy(self.data.get(collection, {}).get(key))

    def find(self, collection, **query):
        with self.lock:
            return [
                copy.deepcopy(d)
                for d in self.data.get(collection, {}).values()
                if all(d.get(k) == v for k, v in query.items())
            ]

    def insert(self, collection, doc):
        with self.lock:
            if self.get(collection, doc["id"]):
                raise DuplicateKeyError("id")
            return self.put(collection, doc)

    def add_user(self, user):
        with self.lock:
            if self.find("users", email=user["email"]):
                raise DuplicateKeyError("email")
            return self.put("users", user)

    def delete(self, collection, key):
        with self.lock:
            self.data.get(collection, {}).pop(key, None)

    def consume(self, collection, key):
        with self.lock:
            return self.data.get(collection, {}).pop(key, None)

    def grant(self, order, event_id):
        with self.lock:
            current = self.get("orders", order["id"])
            if current["status"] == "paid":
                return False
            if self.get("events", event_id):
                return False
            user = self.get("users", order["user_id"])
            current["status"] = "paid"
            user["credits"] += current["credits"]
            self.put("users", user)
            self.put("orders", current)
            self.put("events", {"id": event_id, "order_id": current["id"]})
            self.put(
                "ledger",
                {
                    "id": current["id"],
                    "user_id": user["id"],
                    "delta": current["credits"],
                },
            )
            self.put(
                "outbox",
                {"id": current["id"], "type": "credit.granted", "state": "pending"},
            )
            return True


class SQLiteStore:
    """Single-file persistent store for the local, single-process app."""

    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, timeout=10, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS records ("
            "collection TEXT NOT NULL, id TEXT NOT NULL, email TEXT, "
            "order_code INTEGER, payload TEXT NOT NULL, "
            "PRIMARY KEY (collection, id))"
        )
        self.db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS users_email ON records(email) "
            "WHERE collection = 'users'"
        )
        self.db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS orders_code ON records(order_code) "
            "WHERE collection = 'orders'"
        )
        self.db.commit()

    @staticmethod
    def _encode(doc):
        def encode(value):
            if isinstance(value, datetime):
                return {"__avrt_datetime__": value.isoformat()}
            raise TypeError(f"Unsupported stored value: {type(value).__name__}")

        return json.dumps(doc, default=encode, ensure_ascii=False)

    @staticmethod
    def _decode(payload):
        def decode(value):
            if len(value) == 1 and "__avrt_datetime__" in value:
                return datetime.fromisoformat(value["__avrt_datetime__"])
            return value

        return json.loads(payload, object_hook=decode)

    def _put(self, collection, doc):
        self.db.execute(
            "INSERT INTO records(collection,id,email,order_code,payload) "
            "VALUES(?,?,?,?,?) ON CONFLICT(collection,id) DO UPDATE SET "
            "email=excluded.email, order_code=excluded.order_code, "
            "payload=excluded.payload",
            (
                collection,
                doc["id"],
                doc.get("email") if collection == "users" else None,
                doc.get("order_code") if collection == "orders" else None,
                self._encode(doc),
            ),
        )
        return doc

    def _get(self, collection, key):
        row = self.db.execute(
            "SELECT payload FROM records WHERE collection=? AND id=?",
            (collection, key),
        ).fetchone()
        return self._decode(row[0]) if row else None

    def put(self, collection, doc):
        with self.lock, self.db:
            return self._put(collection, doc)

    def get(self, collection, key):
        with self.lock:
            return self._get(collection, key)

    def find(self, collection, **query):
        with self.lock:
            rows = self.db.execute(
                "SELECT payload FROM records WHERE collection=?", (collection,)
            ).fetchall()
            found = []
            for (payload,) in rows:
                doc = self._decode(payload)
                if all(doc.get(key) == value for key, value in query.items()):
                    found.append(doc)
                    if len(found) == 500:
                        break
            return found

    def insert(self, collection, doc):
        with self.lock, self.db:
            try:
                self.db.execute(
                    "INSERT INTO records(collection,id,email,order_code,payload) "
                    "VALUES(?,?,?,?,?)",
                    (
                        collection,
                        doc["id"],
                        doc.get("email") if collection == "users" else None,
                        doc.get("order_code") if collection == "orders" else None,
                        self._encode(doc),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateKeyError("id or unique field") from exc
        return doc

    def add_user(self, user):
        return self.insert("users", user)

    def delete(self, collection, key):
        with self.lock, self.db:
            self.db.execute(
                "DELETE FROM records WHERE collection=? AND id=?", (collection, key)
            )

    def consume(self, collection, key):
        with self.lock, self.db:
            doc = self._get(collection, key)
            self.db.execute(
                "DELETE FROM records WHERE collection=? AND id=?", (collection, key)
            )
            return doc

    def grant(self, order, event_id):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                current = self._get("orders", order["id"])
                if current["status"] == "paid" or self._get("events", event_id):
                    self.db.rollback()
                    return False
                user = self._get("users", current["user_id"])
                current["status"] = "paid"
                user["credits"] += current["credits"]
                self._put("users", user)
                self._put("orders", current)
                self._put("events", {"id": event_id, "order_id": current["id"]})
                self._put(
                    "ledger",
                    {
                        "id": current["id"],
                        "user_id": user["id"],
                        "delta": current["credits"],
                    },
                )
                self._put(
                    "outbox",
                    {"id": current["id"], "type": "credit.granted", "state": "pending"},
                )
                self.db.commit()
                return True
            except Exception:
                self.db.rollback()
                raise

    def close(self):
        with self.lock:
            self.db.close()


class MongoStore:
    def __init__(self, settings):
        self.client = MongoClient(settings.database_url, serverSelectionTimeoutMS=5000)
        self.client.admin.command("ping")
        hello = self.client.admin.command("hello")
        if not hello.get("setName"):
            raise RuntimeError("MongoDB phải chạy Replica Set để hỗ trợ transactions.")
        self.db = self.client[settings.database_name]
        self.db.users.create_index("email", unique=True)
        self.db.orders.create_index("order_code", unique=True)
        self.db.orders.create_index(
            [("user_id", ASCENDING), ("idempotency_key", ASCENDING)], unique=True
        )
        for name in ("refresh", "tickets", "sessions"):
            self.db[name].create_index("expires_at", expireAfterSeconds=0)
        self.db.sessions.create_index(
            [("user_id", ASCENDING), ("created_at", ASCENDING)]
        )

    def put(self, collection, doc):
        raw = copy.deepcopy(doc)
        raw["_id"] = raw["id"]
        self.db[collection].replace_one({"_id": doc["id"]}, raw, upsert=True)
        return doc

    def get(self, collection, key):
        raw = self.db[collection].find_one({"_id": key}, {"_id": 0})
        return raw

    def find(self, collection, **query):
        return list(self.db[collection].find(query, {"_id": 0}).limit(500))

    def insert(self, collection, doc):
        self.db[collection].insert_one({"_id": doc["id"], **doc})
        return doc

    def add_user(self, user):
        self.db.users.insert_one({"_id": user["id"], **user})
        return user

    def delete(self, collection, key):
        self.db[collection].delete_one({"_id": key})

    def consume(self, collection, key):
        return self.db[collection].find_one_and_delete(
            {"_id": key}, projection={"_id": 0}
        )

    def grant(self, order, event_id):
        def txn(session):
            current = self.db.orders.find_one({"_id": order["id"]}, session=session)
            if current["status"] == "paid" or self.db.events.find_one(
                {"_id": event_id}, session=session
            ):
                return False
            result = self.db.orders.update_one(
                {"_id": order["id"], "status": "pending"},
                {"$set": {"status": "paid"}},
                session=session,
            )
            if not result.modified_count:
                return False
            self.db.events.insert_one(
                {"_id": event_id, "id": event_id, "order_id": order["id"]},
                session=session,
            )
            self.db.ledger.insert_one(
                {
                    "_id": order["id"],
                    "id": order["id"],
                    "user_id": order["user_id"],
                    "delta": order["credits"],
                },
                session=session,
            )
            self.db.users.update_one(
                {"_id": order["user_id"]},
                {"$inc": {"credits": order["credits"]}},
                session=session,
            )
            self.db.outbox.insert_one(
                {
                    "_id": order["id"],
                    "id": order["id"],
                    "type": "credit.granted",
                    "state": "pending",
                },
                session=session,
            )
            return True

        with self.client.start_session() as session:
            return session.with_transaction(txn)


def make_store(settings):
    if settings.database_mode == "memory":
        return MemoryStore()
    if settings.database_mode == "sqlite":
        return SQLiteStore(settings.sqlite_path)
    return MongoStore(settings)
