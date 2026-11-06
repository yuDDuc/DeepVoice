import io
import struct
import sys
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app, now
from app.store import MemoryStore, SQLiteStore
from app.models import Registry, ModelError, verify
from app.billing import Billing, sign


@pytest.fixture
def config():
    return Settings(
        _env_file=None,
        app_env="test",
        database_mode="memory",
        inference_mode="inline",
        jwt_secret="test-only-" + "a" * 40,
    )


@pytest.fixture
def store():
    return MemoryStore()


@pytest.fixture
def client(config, store):
    with TestClient(create_app(config, store)) as client:
        yield client


def csrf(client):
    return {
        "X-CSRF-Token": client.cookies.get("avrt_csrf", ""),
        "Origin": "http://localhost:3000",
    }


def signup(client, email="one@example.com", password="test-password-123"):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
        headers=csrf(client),
    )
    assert r.status_code == 200, r.text
    return r.json()


def translate(client, text="hello"):
    return client.post(
        "/api/v1/translate/text",
        json={"text": text, "direction": "en-vi"},
        headers=csrf(client),
    )


def test_auth_csrf_logout_revokes_access(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    signup(client)
    assert translate(client).status_code == 200
    assert (
        client.post("/api/v1/translate/text", json={"text": "hello"}).status_code == 403
    )
    old = client.cookies.get("avrt_access")
    assert client.post("/api/v1/auth/logout", headers=csrf(client)).status_code == 200
    client.cookies.set("avrt_access", old)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_refresh_rotates_and_replay_fails(client):
    signup(client)
    old = client.cookies.get("avrt_refresh")
    assert client.post("/api/v1/auth/refresh", headers=csrf(client)).status_code == 200
    assert client.cookies.get("avrt_refresh") != old
    client.cookies.set("avrt_refresh", old)
    assert client.post("/api/v1/auth/refresh", headers=csrf(client)).status_code == 401


def test_history_ownership_and_privacy(client):
    signup(client)
    result = translate(client).json()
    ident = result["session_id"]
    assert result["mock"] is True
    assert client.get("/api/v1/sessions/" + ident).status_code == 200
    client.post("/api/v1/auth/logout", headers=csrf(client))
    signup(client, "two@example.com")
    assert client.get("/api/v1/sessions/" + ident).status_code == 404
    assert (
        client.delete("/api/v1/sessions/" + ident, headers=csrf(client)).status_code
        == 404
    )
    assert client.get("/api/v1/admin/audit").status_code == 403
    assert (
        client.patch(
            "/api/v1/settings",
            json={"consent_history": False, "consent_cloud": False},
            headers=csrf(client),
        ).status_code
        == 200
    )
    assert translate(client).json()["saved"] is False
    assert client.get("/api/v1/sessions").json()["sessions"] == []


def test_model_registry_gpu_no_fabrication(client):
    signup(client)
    models = client.get("/api/v1/models").json()["models"]
    assert len(models) == 6
    assert all(m["source"] == "mock" for m in models)
    assert all("local_path" not in m for m in models)
    metrics = client.get("/api/v1/metrics").json()
    assert metrics["gateway"]["remote_gpu"] is None
    assert isinstance(metrics["gateway"]["cpu_percent"], (int, float))
    assert metrics["latency"]["p95_ms"] is None
    translate(client)
    assert client.get("/api/v1/metrics").json()["latency"]["count"] == 1


def test_bad_shapes_and_local_escape(config, tmp_path):
    config.mt_en_vi_source = "local"
    config.mt_en_vi_adapter = "seq2seq"
    config.mt_en_vi_local_path = "../outside"
    registry = Registry(config)
    with pytest.raises(ModelError, match="LOCAL_PATH"):
        registry.preflight("MT_EN_VI")
    config.asr_en_input_shape = "[0]"
    with pytest.raises(ValueError, match="Shape"):
        config.spec("ASR_EN")


def test_relative_model_roots_are_anchored_to_project(monkeypatch, tmp_path):
    from app.config import ROOT

    monkeypatch.chdir(tmp_path)
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_mode="memory",
        inference_mode="inline",
        jwt_secret="test-only-" + "a" * 40,
        local_models_root="./models/custom",
        hf_cache_dir="./models/cache",
        sqlite_path="./data/avrt.sqlite3",
    )
    assert settings.local_models_root == str((ROOT / "models/custom").resolve())
    assert settings.hf_cache_dir == str((ROOT / "models/cache").resolve())
    assert settings.sqlite_path == str((ROOT / "data/avrt.sqlite3").resolve())


def test_sqlite_keeps_account_session_and_history_after_restart(config, tmp_path):
    config.database_mode = "sqlite"
    config.sqlite_path = str(tmp_path / "avrt.sqlite3")
    with TestClient(create_app(config)) as first:
        signup(first, "persistent@example.test")
        result = translate(first).json()
        cookies = dict(first.cookies)
        assert first.get("/api/v1/health").json()["persistent"] is True

    with TestClient(create_app(config)) as second:
        second.cookies.update(cookies)
        assert second.get("/api/v1/auth/me").status_code == 200
        assert second.get("/api/v1/sessions/" + result["session_id"]).status_code == 200
        assert (
            second.post("/api/v1/auth/logout", headers=csrf(second)).status_code
            == 200
        )

    with TestClient(create_app(config)) as third:
        response = third.post(
            "/api/v1/auth/login",
            json={"email": "persistent@example.test", "password": "test-password-123"},
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200, response.text


def test_sqlite_grant_is_idempotent_across_threads(tmp_path):
    store = SQLiteStore(tmp_path / "avrt.sqlite3")
    store.add_user({"id": "u", "email": "u@example.test", "credits": 0})
    order = {"id": "o", "user_id": "u", "credits": 50, "status": "pending"}
    store.insert("orders", order)
    with ThreadPoolExecutor(max_workers=6) as executor:
        outcomes = list(executor.map(lambda _: store.grant(order, "event"), range(12)))
    assert sum(outcomes) == 1
    store.close()
    reopened = SQLiteStore(tmp_path / "avrt.sqlite3")
    assert reopened.get("users", "u")["credits"] == 50
    assert len(reopened.find("ledger")) == 1
    reopened.close()


def test_asr_pipeline_passes_remote_code_policy_only_once(config, tmp_path, monkeypatch):
    model_dir = tmp_path / "asr"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}")
    config.local_models_root = str(tmp_path)
    config.asr_vi_source = "local"
    config.asr_vi_local_path = "asr"
    config.asr_vi_adapter = "transformers_asr"
    captured = {}
    tokenizer = object()

    class FakeTokenizer:
        @staticmethod
        def from_pretrained(target, **kwargs):
            captured["tokenizer_kwargs"] = kwargs
            return tokenizer

    def fake_pipeline(task, **kwargs):
        captured.update(task=task, **kwargs)
        return object()

    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False), float32="f32"),
    )
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            AutoTokenizer=FakeTokenizer,
            AutoModelForSeq2SeqLM=object,
            pipeline=fake_pipeline,
        ),
    )

    Registry(config).load("ASR_VI")

    assert captured["trust_remote_code"] is False
    assert "trust_remote_code" not in captured["model_kwargs"]
    assert captured["model_kwargs"]["local_files_only"] is True
    assert captured["model_kwargs"]["use_safetensors"] is True
    assert captured["tokenizer"] is tokenizer
    assert captured["tokenizer_kwargs"]["extra_special_tokens"] == {}


def test_remote_without_token_and_cloud_consent(client, config):
    config.mt_en_vi_source = "hf_remote"
    config.mt_en_vi_model_id = "example/repo"
    config.mt_en_vi_adapter = "seq2seq"
    with pytest.raises(ModelError, match="HF_TOKEN"):
        Registry(config).preflight("MT_EN_VI")
    config.hf_offline = True
    with pytest.raises(ModelError, match="HF_OFFLINE"):
        Registry(config).preflight("MT_EN_VI")
    signup(client)
    assert translate(client).status_code == 403


def test_websocket_ticket_single_use_origin_seq(client):
    signup(client)
    ticket = client.post("/api/v1/ws-ticket", headers=csrf(client)).json()["ticket"]
    with client.websocket_connect(
        "/ws/v1", headers={"origin": "http://localhost:3000"}
    ) as ws:
        ws.send_json({"ticket": ticket, "direction": "en-vi"})
        ready = ws.receive_json()
        assert ready["type"] == "ready"
        assert ready["mode"] == "buffered_utterance"
        pcm = struct.pack("<h", 2000) * 1600
        ws.send_bytes(struct.pack("<Id", 0, 0) + pcm)
        assert ws.receive_json() == {"type": "ack", "seq": 0}
        ws.send_json({"type": "stop"})
        assert ws.receive_json()["type"] == "processing"
        result = ws.receive_json()
        assert result["type"] == "segment"
        assert result["mock"]
        assert ws.receive_json()["type"] == "done"
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/ws/v1", headers={"origin": "http://localhost:3000"}
        ) as ws:
            ws.send_json({"ticket": ticket})
            ws.receive_json()
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/ws/v1", headers={"origin": "https://evil.example"}
        ):
            pass


def test_wav_upload_and_bad_file(client):
    signup(client)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(struct.pack("<h", 1000) * 1600)
    response = client.post(
        "/api/v1/translate/upload",
        files={"file": ("sample.wav", buf.getvalue(), "audio/wav")},
        data={"direction": "en-vi"},
        headers=csrf(client),
    )
    assert response.status_code == 200, response.text
    assert response.json()["rtf"] is not None
    assert (
        client.post(
            "/api/v1/translate/upload",
            files={"file": ("bad.wav", b"bad", "audio/wav")},
            headers=csrf(client),
        ).status_code
        == 422
    )


def test_audio_upload_allows_up_to_separate_upload_limit(client):
    signup(client)
    sample_rate = 16000
    frames = sample_rate * 10
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(frames * 2))

    response = client.post(
        "/api/v1/translate/upload",
        files={"file": ("ten-seconds.wav", buf.getvalue(), "audio/wav")},
        data={"direction": "en-vi"},
        headers=csrf(client),
    )
    assert response.status_code == 200, response.text


def test_audio_upload_reports_120_second_limit(client):
    signup(client)
    sample_rate = 8000
    frames = sample_rate * 121
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(frames * 2))

    response = client.post(
        "/api/v1/translate/upload",
        files={"file": ("one-hundred-twenty-one-seconds.wav", buf.getvalue(), "audio/wav")},
        data={"direction": "en-vi"},
        headers=csrf(client),
    )
    assert response.status_code == 422
    assert "tối đa 120 giây" in response.json()["detail"]


def test_order_idempotency_and_mock_credit_once(client):
    signup(client)
    headers = {**csrf(client), "Idempotency-Key": "same-order"}
    a = client.post("/api/v1/billing/orders", headers=headers).json()
    b = client.post("/api/v1/billing/orders", headers=headers).json()
    assert a["id"] == b["id"]
    endpoint = "/api/v1/billing/orders/" + a["id"] + "/simulate"
    assert client.post(endpoint, headers=csrf(client)).json()["credited"] is True
    assert client.post(endpoint, headers=csrf(client)).json()["credited"] is False
    assert client.get("/api/v1/billing/wallet").json()["balance"] == 50


def test_signed_webhook_mismatch_duplicate_and_late(config, store):
    config.payment_provider = "payos"
    config.payos_checksum_key = "test-key"
    user = {"id": "u", "credits": 0}
    store.put("users", user)
    order = {
        "id": "o",
        "order_code": 123,
        "user_id": "u",
        "credits": 50,
        "amount_vnd": 50000,
        "currency": "VND",
        "status": "pending",
        "expires_at": now() + timedelta(minutes=5),
        "payment_link_id": "link",
        "account_number": "0123",
    }
    store.put("orders", order)
    gateway = Billing(config, store)
    data = {
        "orderCode": 123,
        "amount": 50000,
        "currency": "VND",
        "code": "00",
        "paymentLinkId": "link",
        "accountNumber": "0123",
        "reference": "bank-unique",
    }
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as e:
        gateway.webhook({"data": data, "signature": "forged"})
    assert e.value.status_code == 401
    wrong = {**data, "amount": 1}
    with pytest.raises(HTTPException):
        gateway.webhook({"data": wrong, "signature": sign(wrong, "test-key")})
    assert store.get("users", "u")["credits"] == 0
    body = {"data": data, "signature": sign(data, "test-key")}
    with ThreadPoolExecutor(max_workers=6) as executor:
        outcomes = list(executor.map(lambda _: gateway.webhook(body), range(12)))
    assert sum(x["credited"] for x in outcomes) == 1
    assert store.get("users", "u")["credits"] == 50
    assert len(store.find("ledger")) == 1
    order.update(
        id="late",
        order_code=124,
        status="pending",
        expires_at=now() - timedelta(minutes=1),
    )
    store.put("orders", order)
    late = {**data, "orderCode": 124, "reference": "bank-late"}
    assert not gateway.webhook({"data": late, "signature": sign(late, "test-key")})[
        "credited"
    ]
    assert store.get("orders", "late")["status"] == "manual_review"
    assert store.get("users", "u")["credits"] == 50


def test_verifier_is_not_semantic_guarantee():
    assert verify("pay 100", "trả 200")["warnings"]
    assert verify("do not pay", "hãy trả tiền")["warnings"]
    assert verify("hello", "xin chào")["semantic_verified"] is False


def test_env_catalog_all_comments_and_fields():
    from app.config import ROOT

    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    fields = set(Settings.model_fields)
    for i, line in enumerate(lines):
        if line and not line.startswith("#"):
            assert i and lines[i - 1].startswith("#"), line
            assert line.split("=", 1)[0].lower() in fields, line
    assert len(
        {
            line.split("=", 1)[0].lower()
            for line in lines
            if line and not line.startswith("#")
        }
    ) == len(fields)
