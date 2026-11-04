from dataclasses import dataclass
import io
import json
import os
import tempfile
import logging
import re
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Use an app-owned Windows cache and disable symlink-based snapshots.
_APP_ROOT = Path(__file__).resolve().parents[2]
_HF_CACHE = _APP_ROOT / '.model-cache'
os.environ.setdefault('HF_HOME', str(_HF_CACHE))
os.environ.setdefault('HF_HUB_CACHE', str(_HF_CACHE / 'hub'))
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS', '1')

@dataclass
class Result:
    text: str
    name: str
    provider: str
    device: str

class MockASR:
    def transcribe(self, audio, name, device):
        return Result('Đây là bản ghi âm mẫu từ DeepVoice.', name, 'mock', device)

class HuggingFaceASR:
    def __init__(self, model_id, device, target_sample_rate=16000, language='en', task='transcribe', chunk_seconds=25, max_new_tokens=448):
        try:
            import torch
            from transformers import AutoProcessor, Wav2Vec2Processor, WhisperFeatureExtractor, WhisperTokenizerFast, WhisperProcessor, AutoModelForCTC, AutoModelForSpeechSeq2Seq
            self.torch = torch
            self.target_sample_rate = target_sample_rate
            self.language = language
            self.task = task
            self.chunk_samples = max(1, int(chunk_seconds)) * target_sample_rate
            self.max_new_tokens = min(440, max(16, int(max_new_tokens)))
            self.is_whisper = 'whisper' in model_id.lower()
            if self.is_whisper:
                # Normalize malformed custom tokenizer metadata in a temp copy. Never
                # edit the user's Hugging Face cache or the model repository.
                from huggingface_hub import snapshot_download
                snapshot = Path(snapshot_download(
                    model_id,
                    cache_dir=str(_HF_CACHE / 'hub'),
                    local_dir=str(_HF_CACHE / 'models' / model_id.replace('/', '--')),
                    local_dir_use_symlinks=False,
                ))
                metadata_path = snapshot / 'tokenizer_config.json'
                metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
                if isinstance(metadata.get('extra_special_tokens'), list):
                    metadata.pop('extra_special_tokens', None)
                    metadata.pop('additional_special_tokens', None)
                    temp_dir = Path(tempfile.mkdtemp(prefix='deepvoice-whisper-'))
                    for source in snapshot.iterdir():
                        if source.is_file():
                            target = temp_dir / source.name
                            if source.name == 'tokenizer_config.json':
                                target.write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf-8')
                            else:
                                target.write_bytes(source.read_bytes())
                    model_source = str(temp_dir)
                else:
                    model_source = model_id
                feature_extractor = WhisperFeatureExtractor.from_pretrained(model_source)
                tokenizer = WhisperTokenizerFast.from_pretrained(model_source, language=language, task=task)
                self.processor = WhisperProcessor(feature_extractor=feature_extractor, tokenizer=tokenizer)
            else:
                self.processor = Wav2Vec2Processor.from_pretrained(model_id)
            model_type = AutoModelForSpeechSeq2Seq if self.is_whisper else AutoModelForCTC
            self.model = model_type.from_pretrained(model_source if self.is_whisper else model_id)
            self.device = 'cuda' if device == 'cuda' or (device == 'auto' and torch.cuda.is_available()) else 'cpu'
            self.model.to(self.device)
            if self.device == 'cpu': self.model.float()
            self.model.eval()
        except Exception as exc:
            raise RuntimeError(f'Không thể load Hugging Face ASR model {model_id}: {exc}') from exc

    def transcribe(self, audio, name, device):
        import soundfile as sf
        import numpy as np
        samples, sample_rate = sf.read(io.BytesIO(audio), dtype='float32', always_2d=False)
        if getattr(samples, 'ndim', 1) > 1: samples = np.mean(samples, axis=1)
        if sample_rate != self.target_sample_rate:
            source_positions = np.arange(len(samples), dtype=np.float32)
            target_length = round(len(samples) * self.target_sample_rate / sample_rate)
            target_positions = np.linspace(0, len(samples) - 1, target_length)
            samples = np.interp(target_positions, source_positions, samples).astype('float32')
            sample_rate = self.target_sample_rate
        if self.is_whisper:
            chunks = [samples[i:i + self.chunk_samples] for i in range(0, len(samples), self.chunk_samples)]
            transcripts = []
            for chunk in chunks:
                if len(chunk) == 0: continue
                inputs = self.processor(chunk, sampling_rate=sample_rate, return_tensors='pt', padding='max_length', max_length=30 * sample_rate, truncation=True)
                model_dtype = next(self.model.parameters()).dtype
                features = inputs['input_features'].to(self.device, dtype=model_dtype)
                with self.torch.inference_mode():
                    prompt_ids = self.processor.tokenizer.get_decoder_prompt_ids(language=self.language, task=self.task)
                    prompt_length = len(prompt_ids) + 1  # include decoder start token
                    token_budget = min(self.max_new_tokens, max(1, 448 - prompt_length))
                    generated = self.model.generate(features, max_new_tokens=token_budget, task=self.task, language=self.language)
                transcripts.append(self.processor.batch_decode(generated, skip_special_tokens=True)[0].strip())
            text = ' '.join(part for part in transcripts if part)
        else:
            inputs = self.processor(samples, sampling_rate=sample_rate, return_tensors='pt', padding=True)
            model_dtype = next(self.model.parameters()).dtype
            inputs = {key: (value.to(self.device, dtype=model_dtype) if value.is_floating_point() else value.to(self.device)) for key, value in inputs.items()}
            with self.torch.inference_mode():
                logits = self.model(**inputs).logits
                text = self.processor.batch_decode(self.torch.argmax(logits, dim=-1))[0].strip()
        return Result(text, name, 'huggingface', self.device)

class MockTranslation:
    def translate(self, text, name, device):
        return Result(f'[Bản dịch mẫu] {text}', name, 'mock', device)

def normalize_translation_input(text):
    text = re.sub(r'\s+', ' ', (text or '').strip())
    if not text:
        return ''
    text = re.sub(r'\bi\b', 'I', text, flags=re.IGNORECASE)
    return text

def chunk_text(text, max_words=25):
    text = normalize_translation_input(text)
    if not text:
        return []
    max_words = max(1, int(max_words))
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    for sentence in sentences:
        words = sentence.split()
        while words:
            part = words[:max_words]
            words = words[max_words:]
            chunk = ' '.join(part)
            if chunk:
                chunk = chunk[0].upper() + chunk[1:]
                chunks.append(chunk)
    return chunks

def remove_repetitions(text):
    text = re.sub(r'<[^>]*>', ' ', text or '')
    text = text.replace('/', '')
    pattern = re.compile(r'(?i)\b((?:[\wÀ-ỹ]+\s+){0,3}[\wÀ-ỹ]+)(?:\s+\1){2,}\b')
    previous = None
    while previous != text:
        previous = text
        text = pattern.sub(r'\1', text)
        text = re.sub(r'\b([\wÀ-ỹ]+)(?:\s+\1){2,}\b', r'\1', text, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', text).strip()

class HuggingFaceTranslation:
    def __init__(self, model_id, device, settings=None):
        try:
            import torch
            from huggingface_hub import snapshot_download
            from pathlib import Path
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            self.torch = torch
            snapshot = Path(snapshot_download(
                model_id,
                cache_dir=str(_HF_CACHE / 'hub'),
                local_dir=str(_HF_CACHE / 'models' / model_id.replace('/', '--')),
                local_dir_use_symlinks=False,
            ))
            self.tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(str(snapshot), local_files_only=True)
            self.device = 'cuda' if device == 'cuda' or (device == 'auto' and torch.cuda.is_available()) else 'cpu'
            self.model.to(self.device)
            if self.device == 'cpu': self.model.float()
            self.model.eval()
            self.model_id = model_id
            self.settings = settings
            self.punctuator = None
            if settings and settings.mt_restore_punctuation:
                from transformers import pipeline
                self.punctuator = pipeline('text2text-generation', model='oliverguhr/fullstop-punctuation-multilang-large', device=0 if self.device == 'cuda' else -1)
        except Exception as exc:
            raise RuntimeError(f'Không thể load Hugging Face Translation model {model_id}: {exc}') from exc

    def translate(self, text, name, device):
        if not (text or '').strip():
            return Result('', name, 'huggingface', self.device)
        settings = self.settings
        if self.punctuator:
            text = self.punctuator(text, max_new_tokens=128)[0]['generated_text']
        chunks = chunk_text(text, settings.mt_max_chunk_words)
        outputs = []
        started = time.perf_counter()
        for offset in range(0, len(chunks), settings.mt_batch_size):
            batch = chunks[offset:offset + settings.mt_batch_size]
            inputs_text = batch
            if 'nllb-200' in self.model_id.lower():
                self.tokenizer.src_lang = 'eng_Latn'
            if 'envit5-translation' in self.model_id.lower():
                inputs_text = [f'en: {part}' for part in batch]
            inputs = self.tokenizer(inputs_text, return_tensors='pt', padding=True, truncation=True, max_length=128)
            model_dtype = next(self.model.parameters()).dtype
            inputs = {key: (value.to(self.device, dtype=model_dtype) if value.is_floating_point() else value.to(self.device)) for key, value in inputs.items()}
            generation = dict(num_beams=settings.mt_num_beams, no_repeat_ngram_size=settings.mt_no_repeat_ngram, repetition_penalty=settings.mt_repetition_penalty, max_new_tokens=settings.mt_max_new_tokens, early_stopping=True)
            if 'nllb-200' in self.model_id.lower():
                generation['forced_bos_token_id'] = self.tokenizer.convert_tokens_to_ids('vie_Latn')
            with self.torch.inference_mode():
                output = self.model.generate(**inputs, **generation)
            outputs.extend(self.tokenizer.batch_decode(output, skip_special_tokens=True))
        cleaned = []
        for output in outputs:
            if 'envit5-translation' in self.model_id.lower():
                output = re.sub(r'^\s*vi:\s*', '', output, flags=re.IGNORECASE)
            result = remove_repetitions(output)
            if result != output.strip():
                logger.warning('MT repetition detected and reduced in chunk')
            cleaned.append(result)
        translated = ' '.join(part for part in cleaned if part)
        logger.info('MT completed: chunks=%d batch_size=%d elapsed_ms=%.1f', len(chunks), settings.mt_batch_size, (time.perf_counter() - started) * 1000)
        return Result(translated, self.model_id, 'huggingface', self.device)

class ModelRegistry:
    def __init__(self, settings):
        self.settings = settings
        if settings.asr_provider.lower() == 'huggingface':
            self.asr = HuggingFaceASR(settings.asr_model_id or settings.asr_model_name, settings.asr_device, settings.asr_sample_rate, settings.asr_language, settings.asr_task, settings.asr_chunk_seconds, settings.asr_max_new_tokens)
        else:
            self.asr = MockASR()
        if settings.mt_provider.lower() == 'huggingface':
            self.mt = HuggingFaceTranslation(settings.mt_model_id or settings.mt_model_name, settings.mt_device, settings)
        else:
            self.mt = MockTranslation()

    def infer(self, audio):
        asr_device = self.settings.asr_device if self.settings.asr_device != 'auto' else 'cpu'
        mt_device = self.settings.mt_device if self.settings.mt_device != 'auto' else 'cpu'
        asr_started = time.perf_counter()
        asr = self.asr.transcribe(audio, self.settings.asr_model_name, asr_device)
        logger.info('ASR completed: elapsed_ms=%.1f', (time.perf_counter() - asr_started) * 1000)
        mt_started = time.perf_counter()
        mt = self.mt.translate(asr.text, self.settings.mt_model_name, mt_device)
        logger.info('MT request completed: elapsed_ms=%.1f', (time.perf_counter() - mt_started) * 1000)
        return asr, mt
