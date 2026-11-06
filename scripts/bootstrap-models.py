"""Download the two public VI->EN models on a fresh checkout.

Weights live in ignored models/custom, outside the Git repository. Existing local
models are kept so an already configured workstation never downloads again.
"""

from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
CUSTOM = ROOT / "models" / "custom"


def complete(folder, names, weight):
    weight_path = folder / weight
    return (
        all((folder / name).is_file() for name in names)
        and weight_path.is_file()
        and weight_path.stat().st_size > 10_000_000
    )


def main():
    original_asr = CUSTOM / "wav2vec2-xlsr-vi-r3"
    public_asr = CUSTOM / "wav2vec2-base-vietnamese"
    base_asr_files = ("config.json", "model.safetensors", "vocab.json", "tokenizer_config.json")
    if complete(
        original_asr, (*base_asr_files, "processor_config.json"), "model.safetensors"
    ):
        print("ASR Việt: dùng model local đã có.", flush=True)
    elif complete(
        public_asr, (*base_asr_files, "preprocessor_config.json"), "model.safetensors"
    ):
        print("ASR Việt: dùng model public đã tải.", flush=True)
    else:
        print("Đang tải ASR Việt (~378 MB) từ Hugging Face...", flush=True)
        snapshot_download(
            repo_id="dragonSwing/wav2vec2-base-vietnamese",
            revision="2d658ec1a90820fee04e9d2edc3cf31ededa4886",
            local_dir=public_asr,
            allow_patterns=[
                "config.json",
                "model.safetensors",
                "preprocessor_config.json",
                "special_tokens_map.json",
                "tokenizer_config.json",
                "vocab.json",
            ],
        )
        if not complete(
            public_asr,
            (*base_asr_files, "preprocessor_config.json"),
            "model.safetensors",
        ):
            raise RuntimeError("Tải ASR chưa đầy đủ; chạy lại script để tiếp tục.")

    mt = CUSTOM / "opus-mt-vi-en"
    mt_files = (
        "config.json",
        "source.spm",
        "target.spm",
        "vocab.json",
        "tokenizer_config.json",
    )
    if complete(mt, mt_files, "model.safetensors") or complete(
        mt, mt_files, "pytorch_model.bin"
    ):
        print("MT Việt → Anh: dùng model local đã có.", flush=True)
    else:
        print("Đang tải MT Việt → Anh (~289 MB) từ Hugging Face...", flush=True)
        snapshot_download(
            repo_id="Helsinki-NLP/opus-mt-vi-en",
            revision="c8d2853e77f5fae31124d993e0b35176b1c8914e",
            local_dir=mt,
            allow_patterns=[
                "config.json",
                "generation_config.json",
                "pytorch_model.bin",
                "source.spm",
                "target.spm",
                "tokenizer_config.json",
                "vocab.json",
            ],
        )
        if not complete(mt, mt_files, "pytorch_model.bin"):
            raise RuntimeError("Tải MT chưa đầy đủ; chạy lại script để tiếp tục.")


if __name__ == "__main__":
    main()
