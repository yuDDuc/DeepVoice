import io, uuid, segno
from datetime import datetime, timezone
from .config import get_settings

settings = get_settings()
def create_invoice(user_id: str, amount: int):
    reference = f"DV{uuid.uuid4().hex[:16].upper()}"
    payload = f"{settings.bank_code}|{settings.bank_account_number}|{amount}|{reference}"
    qr = segno.make(payload); buf = io.BytesIO(); qr.save(buf, kind='png', scale=5)
    return {'reference': reference, 'user_id': user_id, 'amount': amount, 'status': 'pending', 'qr_payload': payload, 'created_at': datetime.now(timezone.utc), 'qr_png_base64': __import__('base64').b64encode(buf.getvalue()).decode()}
