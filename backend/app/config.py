"""One validated settings catalog, including dynamically declared per-role fields."""

import json
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, create_model, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
ROLES = ("ASR_EN", "ASR_VI", "MT_EN_VI", "MT_VI_EN", "TTS_EN", "TTS_VI")
ROLE_DEFAULTS = {
    "SOURCE": "mock",
    "MODEL_ID": "",
    "MODEL_REVISION": "",
    "LOCAL_PATH": "",
    "ADAPTER": "mock",
    "DEVICE": "cpu",
    "DTYPE": "float32",
    "INPUT_SHAPE": "[-1]",
    "OUTPUT_SHAPE": "[-1]",
    "INPUT_SAMPLE_RATE": "16000",
    "INPUT_CHANNELS": "1",
    "ADAPTER_KWARGS_JSON": "{}",
    "PREFIX": "",
}


class ModelSpec(BaseModel):
    role: str
    source: Literal["mock", "hf_hub", "hf_remote", "local"]
    model_id: str
    model_revision: str
    local_path: str
    adapter: Literal["mock", "transformers_asr", "seq2seq", "transformers_tts"]
    device: Literal["cpu", "cuda", "auto"]
    dtype: Literal["float32", "float16", "bfloat16"]
    input_shape: list[int]
    output_shape: list[int]
    input_sample_rate: int = Field(ge=8000, le=96000)
    input_channels: int = Field(ge=1, le=1)
    adapter_kwargs_json: dict
    prefix: str

    @model_validator(mode="after")
    def validate_spec(self):
        if not self.input_shape or any(
            d == 0 or d < -1 for d in self.input_shape + self.output_shape
        ):
            raise ValueError("Shape phải có các chiều >0 hoặc -1 (động).")
        if self.source != "mock" and self.adapter == "mock":
            raise ValueError(
                "Model thật cần adapter tương thích, không dùng adapter mock."
            )
        if self.source in ("hf_hub", "hf_remote") and not self.model_id:
            raise ValueError("HF source cần MODEL_ID.")
        if self.source == "local" and not self.local_path:
            raise ValueError("Local source cần LOCAL_PATH.")
        # No arbitrary Python arguments/remote code from manifests.
        allowed = {
            "max_new_tokens",
            "num_beams",
            "language",
            "task",
            "src_lang",
            "tgt_lang",
        }
        if set(self.adapter_kwargs_json) - allowed:
            raise ValueError("Adapter kwargs không được hỗ trợ; xem docs/MODELS.md.")
        return self


class SettingsBase(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", extra="forbid", case_sensitive=False
    )
    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "AVRT Studio"
    api_port: int = Field(default=8000, ge=1024, le=65535)
    web_port: int = Field(default=3000, ge=1024, le=65535)
    next_public_api_base_url: str = "/api/v1"
    next_public_ws_url: str = "/ws/v1"
    frontend_origin: str = "http://localhost:3000"
    database_mode: Literal["memory", "sqlite", "mongo"] = "mongo"
    sqlite_path: str = str(ROOT / "data/avrt.sqlite3")
    database_url: str = "mongodb://mongo:27017/?replicaSet=rs0"
    database_name: str = "avrt"
    redis_url: str = "redis://redis:6379/0"
    inference_mode: Literal["inline", "redis"] = "redis"
    jwt_secret: str = ""
    cookie_secure: bool = False
    access_token_min: int = Field(default=15, ge=1, le=60)
    refresh_token_days: int = Field(default=14, ge=1, le=90)
    ws_ticket_ttl_seconds: int = Field(default=30, ge=5, le=60)
    auth_rate_limit_per_min: int = Field(default=10, ge=1, le=100)
    enable_registration: bool = True
    local_models_root: str = str(ROOT / "models/custom")
    hf_cache_dir: str = str(ROOT / "models/cache")
    hf_token: str = ""
    hf_offline: bool = False
    hf_remote_provider: str = "hf-inference"
    model_max_new_tokens: int = Field(default=128, ge=1, le=1024)
    max_text_chars: int = Field(default=4000, ge=1, le=20000)
    max_upload_mb: int = Field(default=10, ge=1, le=100)
    max_upload_audio_seconds: int = Field(default=120, ge=1, le=300)
    stream_audio_sample_rate: int = Field(default=16000, ge=8000, le=48000)
    stream_frame_ms: int = Field(default=100, ge=20, le=500)
    stream_buffer_max_ms: int = Field(default=8000, ge=500, le=30000)
    stream_session_timeout_s: int = Field(default=1800, ge=10, le=7200)
    stream_max_sessions_per_user: int = Field(default=2, ge=1, le=4)
    vad_silence_ms: int = Field(default=650, ge=100, le=2000)
    vad_rms_threshold: float = Field(default=0.012, ge=0, le=1)
    telemetry_sample_ms: int = Field(default=1000, ge=500, le=10000)
    telemetry_window_s: int = Field(default=60, ge=1, le=600)
    nvml_enabled: bool = True
    job_timeout_s: int = Field(default=120, ge=1, le=600)
    queue_max_jobs: int = Field(default=20, ge=1, le=100)
    job_result_ttl_s: int = Field(default=300, ge=30, le=3600)
    payment_provider: Literal["mock", "payos"] = "mock"
    payment_test_mode: bool = True
    payment_order_expiry_min: int = Field(default=15, ge=1, le=60)
    credit_package_price_vnd: int = Field(default=50000, ge=1000)
    credit_package_units: int = Field(default=50, ge=1)
    payos_client_id: str = ""
    payos_api_key: str = ""
    payos_checksum_key: str = ""
    payos_api_url: str = "https://api-merchant.payos.vn"
    payment_return_url: str = "http://localhost:3000/app/billing"
    payment_cancel_url: str = "http://localhost:3000/app/billing"
    transcript_retention_days: int = Field(default=30, ge=1, le=365)

    @model_validator(mode="after")
    def safe_mode(self):
        # Resolve portable model directories against the project, not the shell's cwd.
        for key in ("local_models_root", "hf_cache_dir", "sqlite_path"):
            path = Path(getattr(self, key))
            if not path.is_absolute():
                setattr(self, key, str((ROOT / path).resolve()))
        if not self.jwt_secret:
            if self.app_env == "production":
                raise ValueError("Production cần JWT_SECRET ngẫu nhiên >=32 ký tự.")
            self.jwt_secret = secrets.token_urlsafe(48)
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET phải có ít nhất 32 ký tự.")
        if self.app_env == "production" and (
            not self.cookie_secure
            or self.database_mode != "mongo"
            or self.inference_mode != "redis"
        ):
            raise ValueError("Production cần cookie secure, MongoDB và Redis worker.")
        if self.payment_provider == "payos" and not all(
            (self.payos_client_id, self.payos_api_key, self.payos_checksum_key)
        ):
            raise ValueError(
                "payOS cần CLIENT_ID, API_KEY, CHECKSUM_KEY; không mô phỏng giao dịch thật."
            )
        return self

    def spec(self, role: str) -> ModelSpec:
        if role not in ROLES:
            raise ValueError("Role không hỗ trợ.")
        raw = {
            key.lower(): getattr(self, f"{role}_{key}".lower()) for key in ROLE_DEFAULTS
        }
        for key in ("input_shape", "output_shape", "adapter_kwargs_json"):
            raw[key] = json.loads(raw[key])
        return ModelSpec(role=role, **raw)


Settings = create_model(
    "Settings",
    __base__=SettingsBase,
    **{
        f"{role}_{key}".lower(): (
            str,
            "[-1,-1]"
            if (
                key == "INPUT_SHAPE"
                and role.startswith(("MT", "TTS"))
                or key == "OUTPUT_SHAPE"
                and role.startswith("MT")
            )
            else value,
        )
        for role in ROLES
        for key, value in ROLE_DEFAULTS.items()
    },
)


@lru_cache
def get_settings():
    settings = Settings()
    for role in ROLES:
        settings.spec(role)
    return settings
