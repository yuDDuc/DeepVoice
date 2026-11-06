"""Load the bundled offline models and run a minimal real-inference smoke check."""

import io
import struct
import sys
import wave
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

def main():
    from app.config import get_settings
    from app.main import create_app
    from app.store import MemoryStore

    settings = get_settings()
    for role in ("ASR_VI", "MT_VI_EN"):
        spec = settings.spec(role)
        if spec.source != "local":
            raise SystemExit(f"{role} must use local model files, got {spec.source}")
    if settings.inference_mode != "inline":
        raise SystemExit("Smoke check requires INFERENCE_MODE=inline")
    with TestClient(create_app(settings, MemoryStore())) as client:
        transcript = client.app.state.registry.run(
            "ASR_VI", np.zeros(16000, dtype=np.float32)
        )
        registered = client.post(
            "/api/v1/auth/register",
            json={"email": "smoke@example.test", "password": "smoke-password-123"},
            headers={"Origin": settings.frontend_origin},
        )
        registered.raise_for_status()
        response = client.post(
            "/api/v1/translate/text",
            json={"text": "Xin chào, tôi tên là An.", "direction": "vi-en"},
            headers={
                "Origin": settings.frontend_origin,
                "X-CSRF-Token": client.cookies.get("avrt_csrf", ""),
            },
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(transcript, str) or result["mock"] or not result[
            "target_text"
        ].strip():
            raise SystemExit("Real inference returned an invalid result")
        audio = io.BytesIO()
        with wave.open(audio, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\0\0" * 16000)
        uploaded = client.post(
            "/api/v1/translate/upload",
            files={"file": ("silence.wav", audio.getvalue(), "audio/wav")},
            data={"direction": "vi-en"},
            headers={
                "Origin": settings.frontend_origin,
                "X-CSRF-Token": client.cookies.get("avrt_csrf", ""),
            },
        )
        uploaded.raise_for_status()
        if uploaded.json()["mock"]:
            raise SystemExit("Audio upload unexpectedly used mock inference")
        ticket = client.post(
            "/api/v1/ws-ticket",
            headers={
                "Origin": settings.frontend_origin,
                "X-CSRF-Token": client.cookies.get("avrt_csrf", ""),
            },
        )
        ticket.raise_for_status()
        with client.websocket_connect(
            "/ws/v1", headers={"Origin": settings.frontend_origin}
        ) as ws:
            ws.send_json({"ticket": ticket.json()["ticket"], "direction": "vi-en"})
            if ws.receive_json()["type"] != "ready":
                raise SystemExit("WebSocket did not become ready")
            ws.send_bytes(struct.pack("<Id", 0, 0) + struct.pack("<h", 2000) * 1600)
            if ws.receive_json()["type"] != "ack":
                raise SystemExit("WebSocket did not acknowledge audio")
            ws.send_json({"type": "stop"})
            if ws.receive_json()["type"] != "processing":
                raise SystemExit("WebSocket did not begin inference")
            segment = ws.receive_json()
            if segment["type"] != "segment" or segment["mock"]:
                raise SystemExit("WebSocket unexpectedly used mock inference")
            if ws.receive_json()["type"] != "done":
                raise SystemExit("WebSocket did not finish")
        print(f"ASR_VI loaded and transcribed one second of silence: {transcript!r}")
        print(f"MT_VI_EN via API: {result['target_text']}")
        print("Vietnamese audio upload passed through real ASR and MT")
        print("Vietnamese WebSocket audio passed through real ASR and MT")


if __name__ == "__main__":
    main()
