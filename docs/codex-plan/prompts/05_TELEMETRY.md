# PROMPT 05 — Actual CPU/GPU/memory/latency monitoring while translating

Build instrumentation end-to-end, not mock numbers in production. Server-side metrics collector:
- psutil process/system CPU%, RSS, memory available, per-process CPU load, thread count, memory pressure.
- NVIDIA NVML if available: GPU index/name, utilization %, total/used/free VRAM, power/temp when permitted, process VRAM if supported. **GPU utilization is device level** unless specific per-process metric is natively exposed; label this accurately. Expose unsupported/null when no CUDA/NVML, never 0% as equivalent to unavailable.
- ASR/MT/TTS/verifier timings, queue wait, model load/download, audio duration processed, real-time factor (processing seconds divided by audio seconds), confirmed/corrected count, latency distribution P50/P95 over actual observations, provider-mode and revision. For HF_REMOTE: only local request and network latency, no imaginary remote hardware utilization.
- Configurable sample interval, aggregation window, log retention, authenticated `/metrics/sessions/{id}` and rate-limited WS/SSE telemetry. Add Prometheus endpoint optional and JSON endpoint; protect sensitive user metrics, label bounded to avoid high cardinality.
- Frontend dashboard charts that visibly update during mic/translation, model CPU/GPU badges, VRAM/RAM, latency by stage, device/provider label, GPU unavailable notification, download/model load state. Admin view for service metrics, user only sees their session.
- Tests validate CPU-only mode, expected null GPU metrics, multi GPU selection, OS non-support, provider switching, 30s streaming under mock inference and accurate percentile calculations. Avoid high frequency polling of nvidia-smi shell command.

Acceptance: while mock translation runs, process CPU/RAM and pipeline timings shown; GPU metrics appear only where accessible, dashboard updates from real readings. Include metric field dictionary and caveats. STOP.
