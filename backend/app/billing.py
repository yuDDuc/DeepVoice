import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone, timedelta
import httpx
from fastapi import HTTPException


def sign(data, key):
    def normalize(value):
        if value is None:
            return ""
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, (list, dict)):
            return json.dumps(
                value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            )
        return str(value)

    canonical = "&".join(f"{k}={normalize(v)}" for k, v in sorted(data.items()))
    return hmac.new(key.encode(), canonical.encode(), hashlib.sha256).hexdigest()


class Billing:
    def __init__(self, settings, store):
        self.settings, self.store = settings, store

    def create(self, user, key):
        if not key or len(key) > 128:
            raise HTTPException(422, "Idempotency-Key bắt buộc, tối đa 128 ký tự.")
        ident = hashlib.sha256((user["id"] + ":" + key).encode()).hexdigest()
        existing = self.store.get("orders", ident)
        if existing:
            return existing
        settings = self.settings
        order = {
            "id": ident,
            "user_id": user["id"],
            "idempotency_key": key,
            "provider": settings.payment_provider,
            "status": "pending",
            "amount_vnd": settings.credit_package_price_vnd,
            "credits": settings.credit_package_units,
            "currency": "VND",
            "order_code": secrets.randbelow(8_000_000_000_000) + 1_000_000_000_000,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc)
            + timedelta(minutes=settings.payment_order_expiry_min),
            "checkout_url": None,
            "qr_data": None,
            "mock": settings.payment_provider == "mock",
        }
        from pymongo.errors import DuplicateKeyError

        try:
            self.store.insert("orders", order)
        except DuplicateKeyError:
            return self.store.get("orders", ident)
        if settings.payment_provider == "payos":
            fields = {
                "amount": order["amount_vnd"],
                "cancelUrl": settings.payment_cancel_url,
                "description": f"AVRT{order['order_code']}",
                "orderCode": order["order_code"],
                "returnUrl": settings.payment_return_url,
            }
            payload = {
                **fields,
                "signature": sign(fields, settings.payos_checksum_key),
                "expiredAt": int(order["expires_at"].timestamp()),
            }
            try:
                with httpx.Client(timeout=20) as client:
                    response = client.post(
                        settings.payos_api_url + "/v2/payment-requests",
                        json=payload,
                        headers={
                            "x-client-id": settings.payos_client_id,
                            "x-api-key": settings.payos_api_key,
                        },
                    )
                response.raise_for_status()
                body = response.json()
                data = body["data"]
                if body.get("code") != "00" or not hmac.compare_digest(
                    sign(data, settings.payos_checksum_key), body.get("signature", "")
                ):
                    raise ValueError("Bad provider response")
                order.update(
                    checkout_url=data["checkoutUrl"],
                    qr_data=data["qrCode"],
                    payment_link_id=data["paymentLinkId"],
                    account_number=data["accountNumber"],
                    account_name=data.get("accountName"),
                    bank_bin=data.get("bin"),
                    description=data["description"],
                )
            except Exception:
                order["status"] = "provider_error"
                self.store.put("orders", order)
                raise HTTPException(
                    502,
                    "Không tạo được link payOS. Kiểm tra merchant và đối soát orderCode trước khi tạo đơn mới.",
                )
        return self.store.put("orders", order)

    def webhook(self, body):
        settings = self.settings
        if settings.payment_provider != "payos":
            raise HTTPException(503, "payOS chưa cấu hình.")
        data = body.get("data")
        signature = body.get("signature")
        if (
            not isinstance(data, dict)
            or not isinstance(signature, str)
            or not hmac.compare_digest(
                sign(data, settings.payos_checksum_key), signature
            )
        ):
            raise HTTPException(401, "Chữ ký không hợp lệ.")
        matches = self.store.find("orders", order_code=data.get("orderCode"))
        if not matches:
            # payOS registration probe is acknowledged but never credits any wallet.
            return {"accepted": True, "credited": False, "reason": "unmatched_order"}
        order = matches[0]
        if data.get("code") != "00":
            return {"accepted": True, "credited": False}
        if order["status"] == "paid":
            return {"accepted": True, "credited": False, "duplicate": True}
        if (
            data.get("amount") != order["amount_vnd"]
            or data.get("currency") != "VND"
            or data.get("paymentLinkId") != order.get("payment_link_id")
            or data.get("accountNumber") != order.get("account_number")
            or not data.get("reference")
        ):
            raise HTTPException(409, "Thông tin thanh toán không khớp đơn hàng.")
        expiry = (
            order["expires_at"].replace(tzinfo=timezone.utc)
            if order["expires_at"].tzinfo is None
            else order["expires_at"]
        )
        if datetime.now(timezone.utc) > expiry:
            order["status"] = "manual_review"
            self.store.put("orders", order)
            return {
                "accepted": True,
                "credited": False,
                "reason": "late_payment_review",
            }
        granted = self.store.grant(order, "payos:" + data["reference"])
        return {"accepted": True, "credited": granted}
