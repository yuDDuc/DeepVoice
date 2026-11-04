from types import SimpleNamespace
from pymongo import MongoClient
from .config import get_settings

settings = get_settings()

class MemoryCursor:
    def __init__(self, items): self.items = items
    def sort(self, key, direction):
        self.items.sort(key=lambda x: x.get(key), reverse=direction < 0); return self
    def limit(self, count): self.items = self.items[:count]; return self
    def __iter__(self): return iter(self.items)

class MemoryCollection:
    def __init__(self): self.items = []
    def create_index(self, *args, **kwargs): return None
    def insert_one(self, doc):
        doc = dict(doc); doc.setdefault('_id', f'mem-{len(self.items)+1}'); self.items.append(doc)
        return SimpleNamespace(inserted_id=doc['_id'])
    def find_one(self, query):
        return next((x for x in self.items if all(x.get(k) == v for k, v in query.items())), None)
    def find(self, query=None, projection=None):
        query = query or {}; rows = [dict(x) for x in self.items if all(x.get(k) == v for k, v in query.items())]
        if projection:
            for row in rows:
                for key, enabled in projection.items():
                    if enabled == 0: row.pop(key, None)
        return MemoryCursor(rows)

_memory = {}
_mongo = None
if settings.mongodb_url and not settings.mongodb_url.lower().startswith(('disabled', 'memory')):
    try:
        candidate = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=500)
        candidate.admin.command('ping'); _mongo = candidate[settings.mongodb_database]
    except Exception:
        _mongo = None

def collection(name):
    if _mongo is not None: return _mongo[name]
    return _memory.setdefault(name, MemoryCollection())

def ensure_indexes():
    collection('users').create_index('email', unique=True)
    collection('invoices').create_index('reference', unique=True)
    collection('inference_requests').create_index([('user_id', 1), ('created_at', -1)])
