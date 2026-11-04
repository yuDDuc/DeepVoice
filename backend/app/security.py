import base64, hashlib, hmac, os
from datetime import datetime, timedelta, timezone
import jwt

def hash_password(password: str) -> str:
    salt = os.urandom(16); digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 210000)
    return f"pbkdf2$210000${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt, digest = stored.split('$'); actual = hashlib.pbkdf2_hmac('sha256', password.encode(), base64.b64decode(salt), int(rounds))
        return hmac.compare_digest(base64.b64encode(actual).decode(), digest)
    except Exception: return False

def create_token(user_id: str, role: str, secret: str, minutes: int = 30):
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': user_id, 'role': role, 'iat': now, 'exp': now + timedelta(minutes=minutes)}, secret, algorithm='HS256')

def decode_token(token: str, secret: str): return jwt.decode(token, secret, algorithms=['HS256'])
