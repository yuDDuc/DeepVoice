# Cấu hình model

## Format được triển khai

| Role | Adapter | Input | Output | Nguồn |
|---|---|---|---|---|
| ASR_EN / ASR_VI | transformers_asr | waveform float32 `[samples]` | text | Hub, local, HF Remote task ASR |
| MT_EN_VI / MT_VI_EN | seq2seq | token IDs `[batch,sequence]` | token IDs `[batch,sequence]` → text | Hub, local, HF Remote task translation |
| TTS_EN / TTS_VI | transformers_tts | text | WAV PCM16 mono | Hub, local |
| Mọi role | mock | text/audio | minh họa có nhãn | mock |

Đây không phải loader cho mọi model Hugging Face. Whisper tương thích Transformers ASR và các model seq2seq thuộc AutoModelForSeq2SeqLM là đích ban đầu. Adapter hiện chưa hỗ trợ checkpoint PyTorch tùy ý, ONNX/GGUF/CT2, decoder-only chat translation hay code Python tùy biến. Nếu kiến trúc khác, thêm adapter bằng code đã review và contract tests; không sửa business logic pipeline.

## Hugging Face Hub, local inference

Ví dụ minh họa cấu hình, chưa benchmark model trong phiên triển khai:

```dotenv
ASR_EN_SOURCE=hf_hub
ASR_EN_MODEL_ID=openai/whisper-tiny.en
ASR_EN_ADAPTER=transformers_asr
ASR_EN_MODEL_REVISION=
ASR_EN_DEVICE=cpu
ASR_EN_INPUT_SHAPE=[-1]
ASR_EN_ADAPTER_KWARGS_JSON={"language":"english","task":"transcribe"}

ASR_VI_SOURCE=hf_hub
ASR_VI_MODEL_ID=openai/whisper-tiny
ASR_VI_ADAPTER=transformers_asr
ASR_VI_ADAPTER_KWARGS_JSON={"language":"vietnamese","task":"transcribe"}
```

Các model dịch/TTS giữ mock cho đến khi chọn model thích hợp. Tham số language/task phụ thuộc model, model CTC không nhận generate kwargs Whisper. Không sao chép kwargs này cho tất cả ASR.

`hf_hub`: `snapshot_download` tải/cache artifact safetensors/config/tokenizer được allowlist, không tải/chạy `.py` từ repository. Mặc định `trust_remote_code=False`, trọng số yêu cầu safetensors. Lazy-load trên worker khi inference/warmup; UI trạng thái cold/downloading/loading/ready/error, chưa có progress theo byte.

Model công khai có thể không cần token; gated/private cần HF_TOKEN và quyền truy cập model đã được chủ tài khoản chấp nhận. `HF_OFFLINE=true` chỉ dùng cache đã có, không gọi cloud. Pin `*_MODEL_REVISION` bằng commit hash để tái lập. Xóa/đổi cache khi cần do admin thực hiện; không có nút upload code tùy ý.

## Model tự train

Export checkpoint tương thích Transformers:

```python
model.save_pretrained('my-translation', safe_serialization=True)
tokenizer.save_pretrained('my-translation')
# ASR dùng processor.save_pretrained(...) nếu có processor.
```

Copy thành `models/custom/my-translation/`, chứa `config.json`, tokenizer/processor và safetensors. Sau đó:

```dotenv
MT_EN_VI_SOURCE=local
MT_EN_VI_LOCAL_PATH=my-translation
MT_EN_VI_ADAPTER=seq2seq
MT_EN_VI_INPUT_SHAPE=[-1,-1]
MT_EN_VI_OUTPUT_SHAPE=[-1,-1]
MT_EN_VI_DEVICE=cpu
MT_EN_VI_DTYPE=float32
MT_EN_VI_PREFIX=
MT_EN_VI_ADAPTER_KWARGS_JSON={"max_new_tokens":128,"num_beams":2}
```

Dùng PREFIX đúng theo model card/training. Model seq2seq có language-code bắt buộc, forced BOS, input multimodal, hoặc tensor signature khác có thể cần adapter mới. `src_lang`/`tgt_lang` hiện được dùng cho HF Remote; không tự áp vào tokenizer local. Không ép model đa ngôn ngữ hoạt động bằng cách chỉ đổi shape.

Local path bị giới hạn dưới LOCAL_MODELS_ROOT. Shape là khai báo để đối chiếu, không resize trọng số. MT kiểm tra shape token input và output; ASR kiểm tra waveform input; output text ASR và cấu trúc output TTS do adapter chuẩn hóa, không nhận override tensor signature tùy ý.

## HF Remote

Chọn SOURCE=hf_remote, MODEL_ID đúng endpoint/model do provider hỗ trợ, adapter đúng role và HF_TOKEN phía server. Chọn HF_REMOTE_PROVIDER theo hợp đồng provider. Không mặc định mọi repo đều có server inference.

Ví dụ MT tiếng Việt sang Anh qua HF Inference:

```dotenv
MT_VI_EN_SOURCE=hf_remote
MT_VI_EN_MODEL_ID=Helsinki-NLP/opus-mt-vi-en
MT_VI_EN_ADAPTER=seq2seq
HF_REMOTE_PROVIDER=hf-inference
```

Model này chạy qua cloud, cần `HF_TOKEN` phía server và consent cloud của người dùng; nội dung văn bản cần dịch sẽ được gửi tới Hugging Face. Inference Providers có thể yêu cầu credit trả trước (HTTP 402) kể cả khi repo model công khai. Nếu không muốn phụ thuộc credit/provider, dùng `hf_hub` để tải model về và inference local. Endpoint/provider có thể thay đổi theo thời gian.

Người dùng phải bật consent cloud ở Cài đặt trước khi gửi text/audio. TTS remote chưa triển khai và preflight trả lỗi rõ. Lệnh remote hiện batch task translation/ASR; không tuyên bố streaming token từ provider.

## GPU và giới hạn

CPU mặc định. DEVICE=cuda phải có torch CUDA + NVIDIA Container Toolkit; không tự âm thầm chuyển CPU khi user yêu cầu cuda. DEVICE=auto chọn cuda khi có, ngược lại CPU. DTYPE phải tương thích CPU/GPU; float32 an toàn hơn cho CPU nhưng tốn RAM.

```powershell
docker compose -f compose.yaml -f compose.gpu.yaml up --build -d
```

GTX1050 4GB cần kiểm tra hỗ trợ compute capability của bản PyTorch/CUDA trong image. Image GPU chỉ là cấu hình có sẵn để thử, chưa xác nhận hỗ trợ card này. Không bảo đảm model lớn chạy vừa VRAM.

Chưa có quantization, tự unload theo VRAM hoặc chia sẻ trọng số giữa các role. Đổi model rồi recreate worker để giải phóng model cũ. Worker hiện xử lý tuần tự, không tạo nhiều worker trước khi đo RAM.

Nguồn API đối chiếu: https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client ; https://huggingface.co/docs/huggingface_hub/en/guides/download
