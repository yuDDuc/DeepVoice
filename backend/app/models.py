"""Lazy, role-isolated adapters. No model code is trusted/executed from user paths."""

import base64
import io
import re
import time
import wave
from pathlib import Path

import numpy as np

from .config import ROLES


class ModelError(ValueError):
    pass


class Registry:
    def __init__(self, settings):
        self.settings = settings
        self.loaded = {}
        self.states = {r: {"status": "cold", "error": None} for r in ROLES}

    def preflight(self, role):
        spec = self.settings.spec(role)
        if spec.source == "mock":
            return {"ok": True, "note": "Mock: dữ liệu minh họa, không phải model AI."}
        if spec.source == "hf_remote":
            if self.settings.hf_offline:
                raise ModelError("HF_OFFLINE đang bật; không gọi HF Remote.")
            if not self.settings.hf_token:
                raise ModelError(
                    "HF Remote cần HF_TOKEN phía server và model được provider hỗ trợ."
                )
            if role.startswith("TTS"):
                raise ModelError(
                    "HF Remote TTS chưa triển khai; dùng local/Hub transformers_tts."
                )
        else:
            if spec.source == "local":
                root = Path(self.settings.local_models_root).resolve()
                path = (root / spec.local_path).resolve()
                if not path.is_relative_to(root) or not path.is_dir():
                    raise ModelError(
                        "LOCAL_PATH phải là thư mục có sẵn nằm trong LOCAL_MODELS_ROOT."
                    )
                if not (path / "config.json").is_file():
                    raise ModelError(
                        "Thiếu config.json: export bằng save_pretrained(); checkpoint .pt đơn lẻ cần adapter riêng."
                    )
            if spec.device == "cuda":
                try:
                    import torch

                    if not torch.cuda.is_available():
                        raise ModelError(
                            "CUDA không khả dụng; chọn DEVICE=cpu hoặc cài image GPU."
                        )
                except ImportError as exc:
                    raise ModelError("Chưa cài requirements-ai.txt.") from exc
        expected = (
            "transformers_asr"
            if role.startswith("ASR")
            else "seq2seq"
            if role.startswith("MT")
            else "transformers_tts"
        )
        if spec.adapter != expected:
            raise ModelError(f"{role} cần ADAPTER={expected}.")
        # This adapter accepts one waveform (N,) or token ids (B,L). Declaration cannot resize architecture.
        rank = 1 if role.startswith("ASR") else 2
        if role.startswith(("ASR", "MT")) and len(spec.input_shape) != rank:
            raise ModelError(f"INPUT_SHAPE cần rank {rank} cho adapter {spec.adapter}.")
        return {
            "ok": True,
            "note": "Cấu hình hợp lệ; khả năng load model chỉ xác nhận sau warmup/inference.",
        }

    def describe(self):
        result = []
        for role in ROLES:
            spec = self.settings.spec(role)
            public = spec.model_dump(exclude={"local_path", "adapter_kwargs_json"})
            try:
                check = self.preflight(role)
            except (ValueError, ImportError) as e:
                check = {"ok": False, "note": str(e)}
            result.append(
                {
                    **public,
                    **self.states[role],
                    "preflight": check,
                    "execution": "remote" if spec.source == "hf_remote" else "local",
                    "streaming": "buffered_utterance"
                    if role.startswith("ASR")
                    else "batch",
                }
            )
        return result

    def load(self, role):
        self.preflight(role)
        if role in self.loaded:
            return self.loaded[role]
        spec = self.settings.spec(role)
        self.states[role] = {"status": "loading", "error": None}
        try:
            if spec.source == "mock":
                obj = None
            elif spec.source == "hf_remote":
                from huggingface_hub import InferenceClient

                obj = InferenceClient(
                    model=spec.model_id,
                    token=self.settings.hf_token,
                    provider=self.settings.hf_remote_provider,
                    timeout=self.settings.job_timeout_s,
                )
            else:
                import torch
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

                if spec.source == "local":
                    target = str(
                        (
                            Path(self.settings.local_models_root) / spec.local_path
                        ).resolve()
                    )
                else:
                    from huggingface_hub import snapshot_download

                    self.states[role]["status"] = "downloading"
                    target = snapshot_download(
                        repo_id=spec.model_id,
                        revision=spec.model_revision or None,
                        token=self.settings.hf_token or None,
                        cache_dir=self.settings.hf_cache_dir,
                        local_files_only=self.settings.hf_offline,
                        allow_patterns=[
                            "*.json",
                            "*.safetensors",
                            "pytorch_model.bin",
                            "*.model",
                            "*.txt",
                            "*.tiktoken",
                            "tokenizer*",
                            "vocab*",
                            "merges*",
                            "*.spm",
                        ],
                    )
                device = (
                    "cuda"
                    if spec.device == "auto" and torch.cuda.is_available()
                    else "cpu"
                    if spec.device == "auto"
                    else spec.device
                )
                dtype = getattr(torch, spec.dtype)
                opts = {"trust_remote_code": False, "local_files_only": True}
                if role.startswith("MT"):
                    tokenizer = AutoTokenizer.from_pretrained(target, **opts)
                    has_safetensors = (Path(target) / "model.safetensors").is_file()
                    model = (
                        AutoModelForSeq2SeqLM.from_pretrained(
                            target,
                            torch_dtype=dtype,
                            use_safetensors=has_safetensors,
                            weights_only=True,
                            **opts,
                        )
                        .to(device)
                        .eval()
                    )
                    obj = (tokenizer, model, device)
                else:
                    task = (
                        "automatic-speech-recognition"
                        if role.startswith("ASR")
                        else "text-to-audio"
                    )
                    tokenizer = (
                        AutoTokenizer.from_pretrained(
                            target, extra_special_tokens={}, **opts
                        )
                        if role.startswith("ASR")
                        else None
                    )
                    obj = pipeline(
                        task,
                        model=target,
                        tokenizer=tokenizer,
                        device=device,
                        torch_dtype=dtype,
                        trust_remote_code=False,
                        model_kwargs={
                            "local_files_only": True,
                            "use_safetensors": True,
                        },
                    )
            self.loaded[role] = obj
            self.states[role] = {"status": "ready", "error": None}
            return obj
        except Exception as exc:
            # Deliberately avoid remote exception URLs/headers in public diagnostics.
            self.states[role] = {"status": "error", "error": type(exc).__name__}
            raise ModelError(
                f"Không load được {role} ({type(exc).__name__}). Kiểm tra format, revision, cache, quyền HF và RAM/VRAM; model cần safetensors hoặc PyTorch weights_only tương thích."
            ) from exc

    def run(self, role, value):
        spec = self.settings.spec(role)
        obj = self.load(role)
        if spec.source == "mock":
            if role.startswith("ASR"):
                return (
                    "Hello, this is a demonstration."
                    if role == "ASR_EN"
                    else "Xin chào, đây là bản minh họa."
                )
            if role.startswith("MT"):
                known = {
                    "hello": "Xin chào",
                    "thank you": "Cảm ơn",
                    "xin chào": "Hello",
                    "cảm ơn": "Thank you",
                }
                return known.get(value.lower().strip(" .!"), f"[MOCK {role}] {value}")
            return None
        if spec.source == "hf_remote":
            if role.startswith("MT"):
                kwargs = spec.adapter_kwargs_json
                return obj.translation(
                    value,
                    src_lang=kwargs.get("src_lang"),
                    tgt_lang=kwargs.get("tgt_lang"),
                ).translation_text
            audio = np.asarray(value, dtype=np.float32)
            buf = io.BytesIO()
            with wave.open(buf, "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(spec.input_sample_rate)
                f.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
            return obj.automatic_speech_recognition(buf.getvalue()).text
        if role.startswith("ASR"):
            audio = np.asarray(value, dtype=np.float32)
            if audio.ndim != len(spec.input_shape) or any(
                d != -1 and d != actual
                for d, actual in zip(spec.input_shape, audio.shape)
            ):
                raise ModelError("Audio shape không khớp INPUT_SHAPE khai báo.")
            kwargs = {
                k: v
                for k, v in spec.adapter_kwargs_json.items()
                if k in ("language", "task", "max_new_tokens")
            }
            return obj(
                {"raw": audio, "sampling_rate": spec.input_sample_rate},
                generate_kwargs=kwargs,
            )["text"]
        if role.startswith("MT"):
            import torch

            tokenizer, model, device = obj
            tokens = tokenizer(
                spec.prefix + value, return_tensors="pt", truncation=False
            ).to(device)
            actual = list(tokens["input_ids"].shape)
            if any(d != -1 and d != a for d, a in zip(spec.input_shape, actual)):
                raise ModelError(
                    "Token input shape không khớp khai báo. Dùng [-1,-1] cho độ dài động."
                )
            kwargs = {
                k: v
                for k, v in spec.adapter_kwargs_json.items()
                if k in ("max_new_tokens", "num_beams")
            }
            kwargs.setdefault("max_new_tokens", self.settings.model_max_new_tokens)
            with torch.inference_mode():
                output = model.generate(**tokens, **kwargs)
            if len(spec.output_shape) != output.ndim or any(
                d != -1 and d != a for d, a in zip(spec.output_shape, output.shape)
            ):
                raise ModelError(
                    "Token output shape không khớp OUTPUT_SHAPE. MT dùng [-1,-1]."
                )
            return tokenizer.decode(output[0], skip_special_tokens=True)
        out = obj(value)
        audio = np.asarray(out["audio"], dtype=np.float32).reshape(-1)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(out["sampling_rate"])
            f.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
        return {
            "mime": "audio/wav",
            "base64": base64.b64encode(buf.getvalue()).decode(),
        }


def verify(source, target):
    """Heuristics flag risk; passing is not semantic correctness certification."""
    warnings = []
    numbers = lambda s: re.findall(r"\d+(?:[.,]\d+)*", s)
    if sorted(numbers(source)) != sorted(numbers(target)):
        warnings.append("Số liệu khác nhau; cần kiểm tra.")
    neg_en = bool(
        re.search(
            r"\b(?:not|never|no|cannot|can't|don't|doesn't|won't)\b", source, re.IGNORECASE
        )
    )
    neg_vi = bool(re.search(r"\b(?:không|chưa|đừng|chẳng)\b", source, re.IGNORECASE))
    if (neg_en or neg_vi) and not re.search(
        r"\b(?:not|never|no|cannot|không|chưa|đừng|chẳng)\b", target, re.IGNORECASE
    ):
        warnings.append("Có thể mất ý phủ định.")
    if not target.strip():
        warnings.append("Bản dịch trống.")
    return {
        "state": "needs_review" if warnings else "rule_checked",
        "warnings": warnings,
        "scope": "number_negation_heuristics_only",
        "semantic_verified": False,
    }


def infer(settings, registry, job):
    timings = {}
    started = time.perf_counter()
    direction = job["direction"]
    asr = "ASR_EN" if direction == "en-vi" else "ASR_VI"
    mt = "MT_EN_VI" if direction == "en-vi" else "MT_VI_EN"
    text = job.get("text")
    if text is None:
        audio = (
            np.frombuffer(base64.b64decode(job["audio"]), dtype="<i2").astype(
                np.float32
            )
            / 32768
        )
        rate = job["sample_rate"]
        target_rate = settings.spec(asr).input_sample_rate
        if rate != target_rate:
            duration = len(audio) / rate
            audio = np.interp(
                np.arange(int(duration * target_rate)) / target_rate,
                np.arange(len(audio)) / rate,
                audio,
            ).astype(np.float32)
        t = time.perf_counter()
        text = registry.run(asr, audio)
        timings["asr_ms"] = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    target = registry.run(mt, text)
    timings["mt_ms"] = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    check = verify(text, target)
    timings["verify_ms"] = (time.perf_counter() - t) * 1000
    speech = None
    tts_role = "TTS_VI" if direction == "en-vi" else "TTS_EN"
    if job.get("tts") and not check["warnings"]:
        t = time.perf_counter()
        speech = registry.run(tts_role, target)
        timings["tts_ms"] = (time.perf_counter() - t) * 1000
    timings["total_ms"] = (time.perf_counter() - started) * 1000
    duration = job.get("duration_s")
    used = [mt] + ([asr] if "audio" in job else [])
    return {
        "source_text": text,
        "target_text": target,
        "verification": check,
        "state": "needs_review" if check["warnings"] else "confirmed",
        "timings": {k: round(v, 2) for k, v in timings.items()},
        "rtf": timings["total_ms"] / 1000 / duration if duration else None,
        "audio": speech,
        "mock": any(settings.spec(r).source == "mock" for r in used),
        "models": used,
        "direction": direction,
    }
