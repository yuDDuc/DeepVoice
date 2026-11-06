import asyncio
import base64
import hashlib
import io
import json
import math
import secrets
import struct
import time
import wave
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Literal
from uuid import uuid4
import jwt
import numpy as np
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from fastapi import (
    FastAPI,
    Request,
    Response,
    HTTPException,
    Depends,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    Form,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from pymongo.errors import DuplicateKeyError
from .billing import Billing
from .config import get_settings, ROLES
from .jobs import JobRunner
from .models import Registry, ModelError
from .store import make_store
from .telemetry import Telemetry

passwords = PasswordHasher()


def now():
    return datetime.now(timezone.utc)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def create_app(settings=None, store=None):
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app):
        app.state.store = store or make_store(settings)
        app.state.registry = Registry(settings)
        app.state.jobs = JobRunner(settings, app.state.registry)
        app.state.telemetry = Telemetry(settings)
        app.state.billing = Billing(settings, app.state.store)
        app.state.metrics = deque(maxlen=1000)
        app.state.limits = defaultdict(deque)
        app.state.active_ws = defaultdict(int)

        async def sampler():
            while True:
                app.state.telemetry.sample()
                await asyncio.sleep(settings.telemetry_sample_ms / 1000)

        task = asyncio.create_task(sampler())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        if app.state.jobs.redis:
            app.state.jobs.redis.close()
        if hasattr(app.state.store, "close"):
            app.state.store.close()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"],
    )

    @app.middleware("http")
    async def security(request, call_next):
        if (
            request.headers.get("content-length", "0").isdigit()
            and int(request.headers.get("content-length", "0"))
            > settings.max_upload_mb * 1024 * 1024
        ):
            return Response("Request quá lớn", status_code=413)
        if request.method not in (
            "GET",
            "HEAD",
            "OPTIONS",
        ) and not request.url.path.startswith("/api/v1/billing/webhook"):
            origin = request.headers.get("origin")
            if origin and origin != settings.frontend_origin:
                return Response("Origin không hợp lệ", status_code=403)
            if request.cookies.get("avrt_access") or request.cookies.get(
                "avrt_refresh"
            ):
                csrf = request.headers.get("x-csrf-token", "")
                if not csrf or not secrets.compare_digest(
                    csrf, request.cookies.get("avrt_csrf", "")
                ):
                    return Response("CSRF không hợp lệ", status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    def rate_limit(request, bucket, maximum):
        key = bucket + ":" + (request.client.host if request.client else "unknown")
        if app.state.jobs.redis:
            r = app.state.jobs.redis
            count = r.eval(
                "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n",
                1,
                "avrt:limit:" + key,
            )
            if count > maximum:
                raise HTTPException(429, "Quá nhiều yêu cầu, thử lại sau một phút.")
        else:
            values = app.state.limits[key]
            cutoff = time.monotonic() - 60
            while values and values[0] < cutoff:
                values.popleft()
            if len(values) >= maximum:
                raise HTTPException(429, "Quá nhiều yêu cầu, thử lại sau một phút.")
            values.append(time.monotonic())

    def current(request: Request):
        token = request.cookies.get("avrt_access", "")
        try:
            claims = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=["HS256"],
                options={"require": ["exp", "sub", "jti"]},
            )
            session = app.state.store.get("refresh", claims["jti"])
            if (
                not session
                or session.get("revoked")
                or aware(session["expires_at"]) <= now()
            ):
                raise ValueError()
            user = app.state.store.get("users", claims["sub"])
            if not user:
                raise ValueError()
            return user
        except (jwt.PyJWTError, ValueError):
            raise HTTPException(401, "Vui lòng đăng nhập.")

    def admin(user=Depends(current)):
        if user["role"] != "admin":
            raise HTTPException(403, "Cần quyền admin.")
        return user

    def public(user):
        return {k: user[k] for k in ("id", "email", "role", "credits", "created_at")}

    def audit(user, action, **extra):
        app.state.store.put(
            "audit",
            {
                "id": uuid4().hex,
                "actor_id": user["id"],
                "action": action,
                "created_at": now(),
                **extra,
            },
        )

    def tokens(user, response):
        refresh = secrets.token_urlsafe(48)
        ident = digest(refresh)
        expiry = now() + timedelta(days=settings.refresh_token_days)
        app.state.store.put(
            "refresh",
            {
                "id": ident,
                "user_id": user["id"],
                "expires_at": expiry,
                "revoked": False,
            },
        )
        access = jwt.encode(
            {
                "sub": user["id"],
                "exp": now() + timedelta(minutes=settings.access_token_min),
                "jti": ident,
            },
            settings.jwt_secret,
            algorithm="HS256",
        )
        opts = {"secure": settings.cookie_secure, "samesite": "lax", "path": "/"}
        response.set_cookie(
            "avrt_access",
            access,
            httponly=True,
            max_age=settings.access_token_min * 60,
            **opts,
        )
        response.set_cookie(
            "avrt_refresh",
            refresh,
            httponly=True,
            max_age=settings.refresh_token_days * 86400,
            **opts,
        )
        response.set_cookie(
            "avrt_csrf",
            secrets.token_urlsafe(32),
            httponly=False,
            max_age=settings.refresh_token_days * 86400,
            **opts,
        )

    class Credentials(BaseModel):
        email: str = Field(min_length=5, max_length=254)
        password: str = Field(min_length=10, max_length=128)

        @field_validator("email")
        @classmethod
        def valid_email(cls, value):
            if (
                value.count("@") != 1
                or "." not in value.split("@")[1]
                or any(c.isspace() for c in value)
            ):
                raise ValueError("Email không hợp lệ.")
            return value.lower().strip()

    @app.get("/api/v1/health")
    def health():
        return {
            "status": "ok",
            "database_mode": settings.database_mode,
            "inference_mode": settings.inference_mode,
            "persistent": settings.database_mode in ("mongo", "sqlite"),
        }

    @app.post("/api/v1/auth/register")
    def register(data: Credentials, request: Request, response: Response):
        rate_limit(request, "register", settings.auth_rate_limit_per_min)
        if not settings.enable_registration:
            raise HTTPException(403, "Đăng ký đang tắt.")
        user = {
            "id": uuid4().hex,
            "email": data.email,
            "password_hash": passwords.hash(data.password),
            "role": "user",
            "credits": 0,
            "created_at": now(),
            "consent_history": True,
            "consent_cloud": False,
        }
        try:
            app.state.store.add_user(user)
        except DuplicateKeyError:
            raise HTTPException(409, "Email đã tồn tại.")
        tokens(user, response)
        audit(user, "auth.register")
        return public(user)

    @app.post("/api/v1/auth/login")
    def login(data: Credentials, request: Request, response: Response):
        rate_limit(request, "login", settings.auth_rate_limit_per_min)
        users = app.state.store.find("users", email=data.email)
        stored = (
            users[0]["password_hash"]
            if users
            else passwords.hash("dummy-constant-password")
        )
        try:
            passwords.verify(stored, data.password)
        except (VerifyMismatchError, InvalidHashError):
            raise HTTPException(401, "Email hoặc mật khẩu không đúng.")
        if not users:
            raise HTTPException(401, "Email hoặc mật khẩu không đúng.")
        tokens(users[0], response)
        audit(users[0], "auth.login")
        return public(users[0])

    @app.post("/api/v1/auth/refresh")
    def refresh(request: Request, response: Response):
        ident = digest(request.cookies.get("avrt_refresh", ""))
        old = app.state.store.consume("refresh", ident)
        if not old or old.get("revoked") or aware(old["expires_at"]) <= now():
            raise HTTPException(401, "Phiên đã hết hạn.")
        user = app.state.store.get("users", old["user_id"])
        tokens(user, response)
        return public(user)

    @app.post("/api/v1/auth/logout")
    def logout(request: Request, response: Response):
        app.state.store.delete(
            "refresh", digest(request.cookies.get("avrt_refresh", ""))
        )
        for name in ("avrt_access", "avrt_refresh", "avrt_csrf"):
            response.delete_cookie(name, path="/")
        return {"ok": True}

    @app.get("/api/v1/auth/me")
    def me(user=Depends(current)):
        return public(user)

    class Privacy(BaseModel):
        consent_history: bool
        consent_cloud: bool

    @app.get("/api/v1/settings")
    def privacy(user=Depends(current)):
        return {k: user.get(k, False) for k in ("consent_history", "consent_cloud")}

    @app.patch("/api/v1/settings")
    def update_privacy(data: Privacy, user=Depends(current)):
        user.update(data.model_dump())
        app.state.store.put("users", user)
        audit(user, "privacy.update")
        return data

    @app.get("/api/v1/models")
    async def models(user=Depends(current)):
        if app.state.jobs.redis:
            raw = await asyncio.to_thread(
                app.state.jobs.redis.get, "avrt:worker:models"
            )
            if raw:
                return {"models": json.loads(raw), "worker_online": True}
        return {
            "models": app.state.registry.describe(),
            "worker_online": settings.inference_mode == "inline",
        }

    @app.post("/api/v1/models/{role}/warmup")
    async def warmup(role: str, user=Depends(admin)):
        if role not in ROLES:
            raise HTTPException(404, "Role không hỗ trợ.")
        audit(user, "model.warmup", role=role)
        try:
            return await app.state.jobs.run({"action": "warmup", "role": role})
        except ModelError as e:
            raise HTTPException(422, str(e))

    @app.get("/api/v1/metrics")
    async def metrics(user=Depends(current)):
        local = app.state.telemetry.latest or app.state.telemetry.sample()
        worker = None
        if app.state.jobs.redis:
            raw = await asyncio.to_thread(
                app.state.jobs.redis.get, "avrt:worker:metrics"
            )
            if raw:
                worker = json.loads(raw)
        values = [
            m["ms"]
            for m in app.state.metrics
            if m["user_id"] == user["id"]
            and time.monotonic() - m["at"] < settings.telemetry_window_s
        ]
        return {
            "gateway": local,
            "worker": worker,
            "latency": {
                "p50_ms": float(np.percentile(values, 50)) if values else None,
                "p95_ms": float(np.percentile(values, 95)) if values else None,
                "count": len(values),
                "scope": "your_recent_inference",
                "window_s": settings.telemetry_window_s,
            },
        }

    def own_session(ident, user):
        session = app.state.store.get("sessions", ident)
        if not session or session["user_id"] != user["id"]:
            raise HTTPException(404, "Không tìm thấy phiên.")
        return session

    def check_consent(user, direction, audio=False, tts=False):
        roles = [("MT_EN_VI" if direction == "en-vi" else "MT_VI_EN")]
        if audio:
            roles.append("ASR_EN" if direction == "en-vi" else "ASR_VI")
        if tts:
            roles.append("TTS_VI" if direction == "en-vi" else "TTS_EN")
        if any(
            settings.spec(role).source == "hf_remote" for role in roles
        ) and not user.get("consent_cloud"):
            raise HTTPException(
                403, "Cần bật đồng ý gửi dữ liệu lên cloud trong Cài đặt."
            )

    async def execute(user, job, session_id=None):
        check_consent(user, job["direction"], "audio" in job, job.get("tts", False))
        try:
            result = await app.state.jobs.run(job)
        except ModelError as e:
            raise HTTPException(422, str(e))
        except Exception as e:
            raise HTTPException(503, f"Worker không khả dụng ({type(e).__name__}).")
        app.state.metrics.append(
            {
                "user_id": user["id"],
                "ms": result["timings"]["total_ms"],
                "at": time.monotonic(),
            }
        )
        ident = session_id or uuid4().hex
        segment = {
            "id": uuid4().hex,
            "seq": 0,
            "revision": 1,
            "created_at": now().isoformat(),
            **result,
        }
        if user.get("consent_history"):
            existing = app.state.store.get("sessions", ident)
            if existing and existing["user_id"] != user["id"]:
                raise HTTPException(404, "Không tìm thấy phiên.")
            segments = existing.get("segments", []) if existing else []
            if len(segments) >= 500:
                raise HTTPException(413, "Phiên đã đạt giới hạn 500 đoạn.")
            segment["seq"] = len(segments)
            segments.append({**segment, "audio": None})
            app.state.store.put(
                "sessions",
                {
                    "id": ident,
                    "user_id": user["id"],
                    "direction": job["direction"],
                    "created_at": existing["created_at"] if existing else now(),
                    "expires_at": now()
                    + timedelta(days=settings.transcript_retention_days),
                    "segments": segments,
                    "status": "completed",
                },
            )
        return {
            "session_id": ident,
            "saved": bool(user.get("consent_history")),
            **segment,
        }

    class TextInput(BaseModel):
        text: str = Field(min_length=1, max_length=20000)
        direction: Literal["en-vi", "vi-en"] = "en-vi"
        tts: bool = False

    @app.post("/api/v1/translate/text")
    async def translate(data: TextInput, request: Request, user=Depends(current)):
        rate_limit(request, "translate:" + user["id"], 60)
        if len(data.text) > settings.max_text_chars:
            raise HTTPException(413, "Văn bản quá dài theo MAX_TEXT_CHARS.")
        return await execute(user, data.model_dump())

    @app.post("/api/v1/translate/upload")
    async def upload(
        request: Request,
        file: UploadFile = File(...),
        direction: Literal["en-vi", "vi-en"] = Form("en-vi"),
        user=Depends(current),
    ):
        rate_limit(request, "translate:" + user["id"], 60)
        raw = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
        if len(raw) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, "Audio quá lớn.")
        try:
            with wave.open(io.BytesIO(raw)) as wav:
                if (
                    wav.getnchannels() != 1
                    or wav.getsampwidth() != 2
                    or wav.getcomptype() != "NONE"
                ):
                    raise ValueError()
                rate = wav.getframerate()
                frames = wav.getnframes()
                pcm = wav.readframes(frames)
            if (
                rate < 8000
                or rate > 48000
                or not frames
                or len(pcm) != frames * 2
                or frames / rate > settings.max_upload_audio_seconds
            ):
                raise ValueError()
        except (wave.Error, EOFError, ValueError):
            raise HTTPException(
                422,
                f"Cần WAV PCM16 mono 8–48kHz, tối đa {settings.max_upload_audio_seconds} giây.",
            )
        return await execute(
            user,
            {
                "audio": base64.b64encode(pcm).decode(),
                "sample_rate": rate,
                "duration_s": frames / rate,
                "direction": direction,
            },
        )

    @app.get("/api/v1/sessions")
    def sessions(user=Depends(current)):
        records = app.state.store.find("sessions", user_id=user["id"])
        return {
            "sessions": sorted(
                [
                    {k: v for k, v in r.items() if k != "segments"}
                    | {
                        "segment_count": len(r["segments"]),
                        "preview": r["segments"][0]["source_text"]
                        if r["segments"]
                        else "",
                    }
                    for r in records
                ],
                key=lambda r: r["created_at"],
                reverse=True,
            )
        }

    @app.get("/api/v1/sessions/{ident}")
    def session(ident: str, user=Depends(current)):
        return own_session(ident, user)

    @app.delete("/api/v1/sessions/{ident}")
    def delete_session(ident: str, user=Depends(current)):
        own_session(ident, user)
        app.state.store.delete("sessions", ident)
        audit(user, "session.delete", session_id=ident)
        return {"ok": True}

    @app.post("/api/v1/ws-ticket")
    def ticket(user=Depends(current)):
        value = secrets.token_urlsafe(32)
        app.state.store.put(
            "tickets",
            {
                "id": digest(value),
                "user_id": user["id"],
                "expires_at": now() + timedelta(seconds=settings.ws_ticket_ttl_seconds),
            },
        )
        return {"ticket": value, "expires_in": settings.ws_ticket_ttl_seconds}

    @app.websocket("/ws/v1")
    async def stream(ws: WebSocket):
        if ws.headers.get("origin") != settings.frontend_origin:
            await ws.close(code=1008)
            return
        # Authenticate as first frame, never place bearer ticket in URL/logs.
        await ws.accept()
        user = None
        counted = False
        try:
            hello = await asyncio.wait_for(ws.receive_json(), timeout=5)
            record = app.state.store.consume("tickets", digest(hello.get("ticket", "")))
            if not record or aware(record["expires_at"]) <= now():
                await ws.close(code=1008)
                return
            user = app.state.store.get("users", record["user_id"])
            direction = hello.get("direction", "en-vi")
            if direction not in ("en-vi", "vi-en"):
                await ws.close(code=1008)
                return
            check_consent(user, direction, audio=True)
            if app.state.active_ws[user["id"]] >= settings.stream_max_sessions_per_user:
                await ws.close(code=1013)
                return
            app.state.active_ws[user["id"]] += 1
            counted = True
            await ws.send_json(
                {
                    "type": "ready",
                    "sample_rate": settings.stream_audio_sample_rate,
                    "frame_ms": settings.stream_frame_ms,
                    "max_buffer_ms": settings.stream_buffer_max_ms,
                    "mode": "buffered_utterance",
                    "mock": settings.spec(
                        "ASR_EN" if direction == "en-vi" else "ASR_VI"
                    ).source
                    == "mock",
                }
            )
            pcm = bytearray()
            last_seq = -1
            silence_ms = 0
            started = time.monotonic()
            ident = uuid4().hex

            async def flush():
                nonlocal pcm, silence_ms
                if not pcm:
                    return
                payload = bytes(pcm)
                pcm.clear()
                silence_ms = 0
                await ws.send_json({"type": "processing"})
                result = await execute(
                    user,
                    {
                        "audio": base64.b64encode(payload).decode(),
                        "sample_rate": settings.stream_audio_sample_rate,
                        "duration_s": len(payload)
                        / 2
                        / settings.stream_audio_sample_rate,
                        "direction": direction,
                        "tts": bool(hello.get("tts", False)),
                    },
                    ident,
                )
                await ws.send_json({"type": "segment", **result})

            while time.monotonic() - started < settings.stream_session_timeout_s:
                msg = await asyncio.wait_for(
                    ws.receive(), timeout=min(60, settings.stream_session_timeout_s)
                )
                if msg["type"] == "websocket.disconnect":
                    break
                if msg.get("text"):
                    command = json.loads(msg["text"])
                    if command.get("type") == "stop":
                        await flush()
                        await ws.send_json({"type": "done"})
                        break
                    continue
                raw = msg.get("bytes", b"")
                max_frame = (
                    int(
                        settings.stream_audio_sample_rate
                        * settings.stream_frame_ms
                        / 1000
                    )
                    * 2
                    + 12
                )
                if len(raw) < 14 or len(raw) > max_frame or (len(raw) - 12) % 2:
                    await ws.close(code=1009)
                    break
                seq, timestamp = struct.unpack("<Id", raw[:12])
                if seq != last_seq + 1 or not math.isfinite(timestamp):
                    await ws.close(code=1008)
                    break
                last_seq = seq
                audio = raw[12:]
                values = np.frombuffer(audio, dtype="<i2").astype(np.float32) / 32768
                rms = float(np.sqrt(np.mean(values * values)))
                if rms >= settings.vad_rms_threshold or pcm:
                    pcm.extend(audio)
                    silence_ms = (
                        silence_ms
                        + len(audio) / 2 / settings.stream_audio_sample_rate * 1000
                        if rms < settings.vad_rms_threshold
                        else 0
                    )
                await ws.send_json({"type": "ack", "seq": seq})
                if (
                    len(pcm)
                    >= settings.stream_audio_sample_rate
                    * 2
                    * settings.stream_buffer_max_ms
                    / 1000
                    or silence_ms >= settings.vad_silence_ms
                ):
                    await flush()
            await ws.close()
        except (WebSocketDisconnect, asyncio.TimeoutError):
            pass
        except HTTPException as e:
            try:
                await ws.send_json({"type": "error", "message": str(e.detail)})
                await ws.close(code=1011)
            except RuntimeError:
                pass
        except (ValueError, KeyError, TypeError):
            try:
                await ws.close(code=1008)
            except RuntimeError:
                pass
        finally:
            if counted:
                app.state.active_ws[user["id"]] -= 1

    @app.get("/api/v1/billing/capabilities")
    def capabilities():
        return {
            "provider": settings.payment_provider,
            "mock": settings.payment_provider == "mock",
            "google_pay": {"enabled": False, "reason": "Chưa tích hợp PSP Google Pay."},
            "package": {
                "price_vnd": settings.credit_package_price_vnd,
                "credits": settings.credit_package_units,
            },
            "metering_enabled": False,
        }

    @app.get("/api/v1/billing/wallet")
    def wallet(user=Depends(current)):
        return {
            "balance": user["credits"],
            "ledger": app.state.store.find("ledger", user_id=user["id"]),
        }

    @app.post("/api/v1/billing/orders")
    def order(request: Request, user=Depends(current)):
        rate_limit(request, "order:" + user["id"], 10)
        return app.state.billing.create(
            user, request.headers.get("idempotency-key", "")
        )

    @app.get("/api/v1/billing/orders")
    def orders(user=Depends(current)):
        return {"orders": app.state.store.find("orders", user_id=user["id"])}

    def own_order(ident, user):
        order = app.state.store.get("orders", ident)
        if not order or order["user_id"] != user["id"]:
            raise HTTPException(404, "Không tìm thấy đơn.")
        return order

    @app.get("/api/v1/billing/orders/{ident}")
    def get_order(ident: str, user=Depends(current)):
        return own_order(ident, user)

    @app.post("/api/v1/billing/orders/{ident}/simulate")
    def simulate(ident: str, user=Depends(current)):
        if (
            settings.app_env == "production"
            or settings.payment_provider != "mock"
            or not settings.payment_test_mode
        ):
            raise HTTPException(403, "Chỉ dùng mô phỏng trong development/mock.")
        order = own_order(ident, user)
        if now() > aware(order["expires_at"]):
            raise HTTPException(409, "Đơn hết hạn.")
        return {"mock": True, "credited": app.state.store.grant(order, "mock:" + ident)}

    @app.post("/api/v1/billing/webhook/payos")
    async def payos_webhook(request: Request):
        body = await request.body()
        if len(body) > 16384:
            raise HTTPException(413, "Webhook quá lớn.")
        try:
            data = json.loads(body)
        except ValueError:
            raise HTTPException(422, "JSON không hợp lệ.")
        return await asyncio.to_thread(app.state.billing.webhook, data)

    @app.get("/api/v1/admin/audit")
    def admin_audit(user=Depends(admin)):
        return {"events": app.state.store.find("audit")}

    return app


app = create_app()
