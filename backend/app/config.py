from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "DeepVoice"
    environment: str = "development"
    backend_port: int = 8000
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "deepvoice"
    asr_provider: str = "mock"
    asr_model_name: str = "mock-asr"
    asr_model_id: str = ""
    asr_model_path: str = ""
    asr_device: str = "auto"
    asr_sample_rate: int = 16000
    asr_language: str = "en"
    asr_task: str = "transcribe"
    asr_chunk_seconds: int = 25
    asr_max_new_tokens: int = 440
    mt_provider: str = "mock"
    mt_model_name: str = "mock-translation"
    mt_model_id: str = ""
    mt_model_path: str = ""
    mt_device: str = "auto"
    mt_source_language: str = "auto"
    mt_target_language: str = "vi"
    mt_max_chunk_words: int = 25
    mt_batch_size: int = 8
    mt_num_beams: int = 4
    mt_no_repeat_ngram: int = 3
    mt_repetition_penalty: float = 1.2
    mt_max_new_tokens: int = 128
    mt_restore_punctuation: bool = False
    jwt_secret: str = "change-me-in-development"
    auth_required: bool = False
    max_audio_mb: int = 25
    # Luôn đọc .env ở project root, không phụ thuộc terminal đang đứng ở đâu.
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
        case_sensitive=False,
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
