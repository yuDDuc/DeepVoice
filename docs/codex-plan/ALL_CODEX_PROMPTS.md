# AVRT STUDIO — COMPLETE CODEX PROMPTS

Dán `00_MASTER.md` trước và sau đó gửi từng phase. Bản này là toàn bộ prompt để tiện copy.

See `README_START_HERE.md` and `.env.example` for setup.


---

## 00_MASTER.md
# PROMPT 00 — GLOBAL OPERATING CONTRACT (send first)

You are the lead engineer/architect responsible for shipping **AVRT Studio**, an EN ⇄ VI realtime translation platform. Work INSIDE THE CURRENT REPOSITORY and implement code rather than merely describing a plan. Communicate results and documentation in Vietnamese; use English for identifiers, APIs, code, schema names and tests.

Read these files first and follow them in priority: `docs/codex-plan/reference/SYSTEM_REQUIREMENTS.md`, `docs/codex-plan/reference/ENV_CONTRACT.md`, `docs/codex-plan/.env.example`, and every phase prompt as I provide it. If the files were copied elsewhere, discover them safely and show the resolved paths.

RULES:
1. Work in **gated checkpoints**. Do only the phase I provide. Add minimal interfaces/placeholders needed for integration, never falsely claim that later phases are done. Before work inspect existing code and preserve it; never delete/reset user files or Git work without approval.
2. For each phase: (a) inspect, (b) state concise implementation plan, (c) implement, (d) run formatter/linter/typed checks/tests, (e) update `docs/IMPLEMENTATION_STATUS.md`, (f) explain how to run/test, what remains, then STOP. If time/tool limit hits, leave resumable state and explicit next commands; do not fake execution.
3. All tunable values must be declared in `.env.example` with a directly preceding **Vietnamese `#` comment** explaining usage, allowed values, units, defaults and whether restart is necessary. Actual secrets go into ignored `.env`; `.env.example` uses safe blanks. Validate configuration on boot, redact tokens/passwords in logs and APIs. For browser, expose only allowed `NEXT_PUBLIC_*` values; not HF tokens or bank/payment keys. Read env on server startup; do not secretly hardcode model choices, dimensions, chunk sizes, price ratios or endpoints.
4. Build independent, contract-tested adapters and registry. I must be able to train models elsewhere, copy custom weights into an allowed local folder, set ENV source/adapter/path/input/output specifications, restart/reload safely, and use them without rewriting business logic. Where format incompatibility makes that impossible, fail with actionable validation and explain the required adapter. Default `trust_remote_code=false`.
5. Separate **HF Hub downloading and local inference** from **HF Inference remote API**. Download only selected compatible model artifacts lazily/resumably, cache/pin revision, share a persistent volume, report status/progress; never imply HF can execute every named model remotely. Streaming mic audio/subtitles != streaming HF weight files. Ensure CPU mock demo works without HF token or NVIDIA GPU.
6. Production-minded: schema validation, CORS, auth, authz, CSRF, rate limiting, request size caps, secure WebSockets, secrets handling, audit trails, retry/backoff/idempotency, Docker healthchecks and replica-set MongoDB transactions. Do NOT call a self-created VietQR image a confirmed payment, and do not enable Google Pay without a PSP.
7. Create all diagrams as editable Mermaid source: logical Mongo ERD, network & role access, WebSocket inference sequence, HF model load state, signed payment webhook flow.
8. Make runtime metrics honest: local CPU/RAM/process, local GPU/VRAM only if measurable; cannot know HF remote hardware from local client. Expose timestamps, windows and actual source.
9. Write meaningful tests for bad shape, HF offline/no token, CPU-only, websocket disconnect, concurrent sessions, payment webhook duplicate/out-of-order/signature failure, user authorization and rollback.
10. Never execute untrusted download or arbitrary `trust_remote_code`. Keep voice samples and speaker embeddings consent-gated and user-removable.

At the start, inspect repo and report: existing stack, incompatible files, tasks for the current phase, and blocking external credentials. Choose safe mock equivalents when credentials are missing, without asking me to paste secrets in chat.


---

## 01_ARCHITECTURE.md
# PROMPT 01 — System architecture, ERD, API and access/data flows

Read MASTER + SYSTEM_REQUIREMENTS + ENV_CONTRACT. Create real `docs/architecture/` and architecture decision records before writing application code. Deliver:

1. `ARCHITECTURE.md`: components (Next.js frontend, FastAPI API, FastAPI WS gateway, inference worker, Redis, MongoDB replica set, HF Hub cache, optional payment gateway), trust boundaries and CPU/GPU topology; argue why per-role model adapters keep custom weights swappable.
2. **Five editable Mermaid diagrams**:
   - `erd.mmd`: Mongo collections users, refresh_sessions, consents, speaker_profiles, model_registry, translation_sessions, transcript_segments, metric_samples, plans, subscriptions, payment_orders, payment_events, wallet_accounts, wallet_ledger, audit_events, webhook_inbox, outbox. Show logical relations, important field types/keys and cardinality. Explain embedded vs referenced fields and indexes/TTL (no claim that Mongo is SQL).
   - `access_flow.mmd`: anonymous/user/admin, route and model permissions, public webhook ingress, API/WS, worker, database, billing provider, HF.
   - `streaming_sequence.mmd`: mic browser -> authenticated WS -> buffering/VAD -> ASR -> MT -> verifier -> subtitles/TTS; interim/confirmed/corrected, recovery, switch direction, metrics; no TTS on unverified risky provisional content.
   - `hf_model_lifecycle.mmd`: unconfigured -> validating -> fetching -> cached -> warming -> ready -> unloading/error; optional HF remote branch and local path preflight.
   - `payment_sequence.mmd`: user -> API creates pending order -> payOS/SePay checkout -> provider verified webhook -> inbox dedup -> DB transaction -> ledger/wallet/entitlement -> client status. Include `expired`, unknown payments, reconciliation; Google Pay via PSP branch only.
3. `API_CONTRACT.md` with REST endpoints and JSON request/response examples, roles/rate limits; versioned WS schema incl audio chunk binary frames, sequencing, backpressure and metrics feed. Identify streaming resampling boundaries and clock standards.
4. `DATA_DICTIONARY.md` defining immutable ledger rules, receipt status machine and indexes/unique constraints; `ADRs/` for model plugin choices, Mongo transactions, credential handling, ARM edge strategy.
5. `ROADMAP.md` track stages 1–8: core translation, verified realtime, two-way S2S, speaker/predictive adaptation, hybrid/quant, board benchmarks, physical prototype, PCB Rev A. Map implementation phases 02–10 to these stages.

Don't claim prototype code exists. Validate Mermaid grammar with an available renderer if installed; otherwise document static checks and syntax assumptions. End with a readable dependency/acceptance checklist and STOP.


---

## 02_FOUNDATION.md
# PROMPT 02 — Monorepo + infrastructure foundation

Implement the scaffold, not a toy. Read all docs created in phase 01. Recommended layout:

`apps/web` Next.js + TS + Tailwind + shadcn/ui; `services/api` FastAPI/Pydantic; `services/inference` separate Python worker with abstract model interfaces; `packages/contracts` shared JSON schemas/types; `infra/docker` and `infra/scripts`; `docs/architecture`; `tests/` for end-to-end integration.

Requirements:
- Python dependency manager with lock file; typed Pydantic settings from env; JS lock; consistent commands `make setup/dev/test/lint` or portable scripts incl Windows PowerShell variants.
- `docker-compose.yml` CPU default services: web, api, inference, mongo, mongo-rs-init, redis; persistent volumes for HF cache and Mongo; healthchecks, service dependencies, restart policies, non-root where feasible. Mongo **single-node replica set for dev only** to exercise multi-document transactions; document production 3-node setup and limitations. Distinct GPU compose override/profile for NVIDIA; CPU-only must still start without toolkit.
- Redis for ephemeral queues and progress; avoid storing secrets or audio in events. Mongo connection readiness and bootstrap unique indexes/TTL. Optional object storage adapter uses local secure volume for MVP, not arbitrary public static file URLs.
- `/health/live`, `/health/ready`, `/version`, GET `/api/v1/config/public` and a typed WS handshake. API OpenAPI and error schema. Real API integration on frontend scaffold.
- `.env.example` must be canonical annotated; `scripts/check_env.py` checks supported enum and shape syntax and reports missing *optional* credentials without preventing mock mode. Separate `.env` ignored by Git, secret scrubber.
- CI minimal lint/typecheck/unit tests, dev smoke test, README with exact commands. Add Docker image build cache and lazy model downloads; do not pull gigabytes of model weights at build time.

Acceptance: fresh clone + sample env + one command starts CPU mock infrastructure, web connects to API, Mongo transactions succeed in replica set, tests pass. If Docker unavailable in Codex environment, give reproducible commands and show what static checks actually ran. STOP.


---

## 03_MODELS.md
# PROMPT 03 — Hugging Face + own-model pluggable registry

Build an actually functional model plugin system for roles ASR_EN, ASR_VI, MT_EN_VI, MT_VI_EN, TTS_EN, TTS_VI, VERIFIER, PREDICTOR, SPEAKER_EMBEDDER. This is the highest-priority design contract: **a user-trained model can be added by copying model artifacts into a configured directory and editing `.env`** (plus a format-compatible adapter if not supported).

1. `ModelSpec` strongly typed: role, source (`hf_hub|hf_remote|local|mock`), model_id/path, revision/sha, adapter (`transformers_seq2seq|ct2|whisper|onnx|custom_manifest|mock|...`), device/dtype/quant, language/task, declared input shape and output schema, audio rate/channels, chunk/stride, batch, kwargs. Read spec from env per role with early validation. Do not assume one model for both speech and text, or that every role is active.
2. `ModelAdapter` protocol: validate_spec(), capabilities(), prepare(), load(), warmup(), infer()/stream() when supported, unload(), metrics(); cleanup/cancel. `ModelRegistry`, `LocalAdapter`, `HFHubAdapter`, `HFRemoteAdapter`, `MockAdapter`, plus concrete working examples for one compatible ASR and NMT family. Preserve input/output type safety; no silent shape coercion. Have `custom_manifest.json` example specifying expected files and shapes. A non-supported model format returns helpful errors rather than placeholder success.
3. HF Hub: implement `snapshot_download`/`hf_hub_download` with pinned revision, allow patterns where possible, persistent cache volume, progress lifecycle, disk/VRAM checks, download retry and offline mode. Auth token from backend env only. Do not load arbitrary remote Python; default `trust_remote_code=false`. Document licensing and model access approval.
4. HF Remote: optional `InferenceClient` adapter for supported tasks/provider capabilities, API credentials and timeout/retry; test remote readiness and distinguish remote text streaming from ASR chunk requests. If remote task unavailable, surface `unsupported` and optionally revert to local according to routing policy.
5. Switchover with active sessions: versioned model handle, model loading lock/refcount, readiness, rollback, memory budgets and error isolation. No hot swap corrupting active streams. `GET /models`, `/models/{role}/status`, `/models/{role}/validate`, protected admin `/models/{role}/warmup`, `/models/{role}/reload` and progress endpoint/WS. Protect local paths with allowlist to prevent directory traversal.
6. Tests: mock, local fixture and optional gated real HF integration. Test offline cached mode, wrong tensor shape, incompatible adapter, secret redaction, model swap during inference, disk quota, no GPU and remote unavailable. Documentation: `docs/MODEL_SWAP_GUIDE_VI.md` with step-by-step instructions to plug trained Wav2Vec2, Whisper-compatible ASR, EnViT5 and custom ONNX/CT2 weights.

Acceptance: one env change switches compatible model source `mock -> hf_hub -> local`; app reports actual chosen provider and revision, run basic inference or explicit compatible fixture; no pipeline code edits. STOP.


---

## 04_STREAMING.md
# PROMPT 04 — Verified realtime bidirectional translation engine

Implement actual audio and translation orchestration using the provider interfaces. Phased feature flags in env enable deterministic baseline first; improve only with measurable results.

A. Mic/audio protocol: authenticated short-lived WS token, client captures audio with AudioWorklet when possible, 16-bit PCM chunks or negotiated encoded frames (not base64 JSON for continuous audio), sample_rate/channel/header negotiated, frames with monotonic timestamps and sequence IDs; resample, VAD, ring buffer, max size, backpressure, deadline, cancel/reconnect. Mock stream simulates exact event contract without model.
B. ASR stability: incremental partial hypotheses, utterance finalization, stable prefix, word/chunk timestamps when available, diarization/speaker ID plugin optional. The remote HF ASR adapter may not be true incremental; implement measured chunk-window fallback and disclose this in UI.
C. NMT en_vi + vi_en; detect direction by manual switch/PTT first, optional auto language ID; preserve named entities, numbers, negation, units, code-switch. Segment statuses `partial`, `stable`, `confirmed`, `corrected`, `error`; idempotent, ordered event emission; versioned corrections to earlier text. Define clear handling for a context inversion ("not ...") and cancellation.
D. Fast verification: exact token/regex/locale-aware number+unit handling, negation and condition flags, named entities; source-aligned warnings, don't assert semantic correctness from heuristics alone. Optional deep semantic verifier behind adapter; never automatically 'fix' without evidence. TTS only confirmed chunks; if unsafe/uncertain, mark review and prefer wait/mute. Explain limitations.
E. TTS both directions with audio frames, queue, chunk playback, voice profiles; echo mitigation using PTT/headphones plus optional AEC when available; no false low-latency promises.
F. Stage 04 feature flags: speaker context memory ONLY with user consent, accent/code-switch evaluation, predictive prefetch translation without speaking unconfirmed predictions, adaptive wait-k timing, hybrid local/cloud failover preserving order and session state. If model/provider lacks support, display feature unavailable. No automatic fine-tune based on unverified transcripts.
G. Streaming session storage and export, metrics hooks for every step; cap memory and processing costs per session/plan. Add deterministic test audio fixture and integration tests for partial corrections, numerical changes, rapid speaker switching, disconnect, backpressure, cloud failure and privacy opt-out.

Deliver REST upload endpoint and live WS flow plus integration with a minimal frontend view. Target initial P95 finalized subtitle < 4s on test PC as an engineering **target to measure**, not claim. Tests + docs `STREAMING_PROTOCOL.md`, `PERFORMANCE_BASELINE.md`. STOP.


---

## 05_TELEMETRY.md
# PROMPT 05 — Actual CPU/GPU/memory/latency monitoring while translating

Build instrumentation end-to-end, not mock numbers in production. Server-side metrics collector:
- psutil process/system CPU%, RSS, memory available, per-process CPU load, thread count, memory pressure.
- NVIDIA NVML if available: GPU index/name, utilization %, total/used/free VRAM, power/temp when permitted, process VRAM if supported. **GPU utilization is device level** unless specific per-process metric is natively exposed; label this accurately. Expose unsupported/null when no CUDA/NVML, never 0% as equivalent to unavailable.
- ASR/MT/TTS/verifier timings, queue wait, model load/download, audio duration processed, real-time factor (processing seconds divided by audio seconds), confirmed/corrected count, latency distribution P50/P95 over actual observations, provider-mode and revision. For HF_REMOTE: only local request and network latency, no imaginary remote hardware utilization.
- Configurable sample interval, aggregation window, log retention, authenticated `/metrics/sessions/{id}` and rate-limited WS/SSE telemetry. Add Prometheus endpoint optional and JSON endpoint; protect sensitive user metrics, label bounded to avoid high cardinality.
- Frontend dashboard charts that visibly update during mic/translation, model CPU/GPU badges, VRAM/RAM, latency by stage, device/provider label, GPU unavailable notification, download/model load state. Admin view for service metrics, user only sees their session.
- Tests validate CPU-only mode, expected null GPU metrics, multi GPU selection, OS non-support, provider switching, 30s streaming under mock inference and accurate percentile calculations. Avoid high frequency polling of nvidia-smi shell command.

Acceptance: while mock translation runs, process CPU/RAM and pipeline timings shown; GPU metrics appear only where accessible, dashboard updates from real readings. Include metric field dictionary and caveats. STOP.


---

## 06_AUTH_DB.md
# PROMPT 06 — Production-oriented auth, RBAC and Mongo persistence

Implement users, hashed passwords (Argon2id), signup/signin/refresh/signout/session revocation, optional email verification, forgot/reset password via configured mail adapter (mock in dev); access token in secure HttpOnly cookie with CSRF strategy and SameSite, refresh rotation/reuse detection. Short-term WS ticket bound to user/session. Support roles `user|admin`, resource scoping and admin audit log; reject unauthorized model registry updates and other-user session access. Rate limit login, token issue and WebSockets; secure CORS and secret redaction.

Implement Mongo logical entities from ERD: users, sessions, consents, speaker_profiles, model_registry, translation_sessions, transcript_segments, metrics and audit. Indexes: unique email, unique external provider events/idempotency where applicable, TTL for ephemeral sessions/tokens/metrics, `user_id + created_at` for history. Use encrypted or protected storage strategy for optional raw audio; default no long-term audio retention. Provide delete-my-data API including associated speaker embeddings within documented retention/legal constraints.

Build DB transaction wrapper and unit-test with the dev replica set, explain non-HA single-node mode; keep external calls out of transactions. Testing with two users, admin/user scopes, expired cookie, stolen/reused refresh, CSRF, WS access, consent disabled, deletion and transaction rollback. Backend integration docs and frontend typed auth contracts. STOP.


---

## 07_BILLING.md
# PROMPT 07 — Transaction-ready billing: VietQR, payOS, SePay, Google Pay

Implement real accounting discipline with a mock-first checkout. Supported payment providers behind `PaymentProvider` interface: `mock`, `payos` (primary Vietnam VietQR), optional `sepay`, and `google_pay_psp` **only if a supported processor and merchant credentials exist**. Do not conflate Google Pay wallet tokens with bank transfer. Only approved/tested PSP can charge; otherwise disable button with configuration/status message.

- Plans/prices and credit calculation from env / server-side versioned catalog. Backend computes final amount (integer VND) and order id; client cannot set credited amount. Generate unique orderCode/reference; pending order with expiration, provider payment link or **dynamic VietQR containing bank account, account name, amount and unique transfer message**. Show expiry clock and pending/paid/failed/refunded/manual_review. Never display fake success when scanning QR; bank notifications/provider webhooks must confirm.
- `POST /api/v1/billing/orders`, GET order/status, GET subscriptions/wallet/ledger, protected admin reconciliation/refund endpoints (only implement provider refund if officially supported). Input idempotency key and immutable local order pricing snapshot.
- payOS: server SDK/API payment link with valid settings; validate HMAC webhook signature per current official docs; reject replay/duplicate; orderCode/amount/currency/reference compare. SePay optional webhook verification strategy per provider docs, bank account/reference checks. Store sanitized raw event in durable `webhook_inbox` w/ unique provider event ID or canonical reference hash, processed state. Acknowledge only after durable storage, replay async safely.
- Within short Mongo DB transactions: transition order pending→paid once; insert immutable wallet_ledger credit entry; update wallet balance/entitlement (or derive balance from ledger with compact snapshot) exactly once; write outbox event. Create unique indexes to enforce idempotency and concurrency safety. Race conditions: repeated / delayed / out-of-order webhook, partial/under/overpayment, expired order, mismatch, duplicate reference -> manual_review/reconciliation, not unconditional credit.
- Important: Mongo transaction requires replica-set; test rollback/failover modes. Never grant credits based on frontend redirect/receipt screenshot or query parameter.
- Optional Google Pay: integrate via a *documented PSP adapter*, with proper merchant eligibility, tokenization handling, test mode and processor-confirmed success. If no PSP chosen, implement interface + fully disabled UI and docs, not fake active checkout.
- No real charged operation in CI. Use fixture-signed provider samples and dedicated mock webhook simulator; event log, admin test harness, pending→paid acceptance test without using bank accounts. Do not put API keys in screenshots or frontend.

Acceptance: duplicate signed webhook triggers **one** ledger credit; invalid signature, wrong amount and replay trigger zero credits; UI status changes only after server persistence. Output `docs/BILLING_PROVIDER_SETUP_VI.md` (registration steps, webhook public HTTPS, sandbox vs prod, required keys, testing and reconciliation). STOP.


---

## 08_FRONTEND.md
# PROMPT 08 — Complete Next.js FE integrated with real BE

Implement a responsive, Vietnamese-first UI with dark/light theme and accessibility. Pages:
`/` landing/value; `/auth/login`, `/auth/register`, `/auth/forgot`; `/app/translate/live` two-way mic, live waveform, partial/confirmed/corrected EN/VI dual transcript, talk button, speaker badges, provider/local state, subtitles+TTS controls, verification warnings; `/app/translate/upload`; `/app/history` session list/detail/export/delete; `/app/models` active role/model/source/revision/health/validate/download status with admin controls gated; `/app/monitor` realtime CPU/GPU/VRAM/RAM/latency/P50/P95 + no-NVML fallback; `/app/billing` plans, balance, buy credits, VietQR modal with amount/account/description/copy, status polling/socket, invoice/history; `/app/settings` privacy, audio retention, speaker memory, profile; `/admin` protected controls, audit and reconciliation.

All UI must use typed real API/WS clients with mocked BE **only in explicit mock mode**. No hardcoded empty business success. Source of truth for role model settings in backend env; UI may request permitted runtime selection but not expose secrets. Handle mic permission failure, mobile layout, reconnect, slower-than-realtime warnings, provider fallback, QR payment pending, token expiry, offline network.

For metrics use genuinely live data or clear 'unavailable'. For payments use server-provided QR/link + merchant metadata; Google Pay shows only when `capabilities.google_pay.enabled=true` from server. Screenshots/Playwright tests at 1440px and 375px, key flows. Simple elegant SaaS aesthetic; meaningful loading/skeleton/error and empty states, no generated static 'fake' prices in production.

Acceptance: end-to-end sign-in → mock live translate → monitor → save/export → mock checkout → credit balance view; two-account authorization negative test; responsive screenshots and FE tests. STOP.


---

## 09_PRODUCTION.md
# PROMPT 09 — Docker, test, security, release and observability hardening

Make repository reproducible and production-minded without claiming hardware/payment certification:

- Compose CPU startup must work with no GPU; optional `compose.gpu.yml` verified against NVIDIA Container Toolkit. No HF model downloads in Docker build; named persistent cache. Mongo dev replica set bootstrapped deterministically; production docs require appropriate multi-node replica set, secure credentials, backups and restore test. Redis health, inference worker queue and WS ingress. Limit CPU/RAM and number of concurrent streams via env.
- Security audit: dependency scan/lock, secrets scanning, origin checks, cookie flags for prod, CSRF, WebSocket ticket, per-route RBAC, request caps and content-type validation, path traversal for local model directories, no arbitrary `trust_remote_code`/pickle loads by default, streaming quotas, PII redaction. Verify privacy and consent for raw audio and speaker profiles.
- Integration/e2e test matrix: mock CPU, local fixture, optional HF_HUB, optional HF_REMOTE, CUDA available, disconnection/reconnect, dynamic model swap, no Internet, partial correction, high-risk negation, concurrent users, duplicate webhook, bad signature, transaction rollback, frontend billing flow. Load test realistic audio chunks; document P50/P95/RTF and RAM/VRAM actually measured, along with machine specs.
- CI workflow: lint/typecheck/unit/integration/e2e, skip gated external tests clearly. Documentation: INSTALL_WINDOWS.md (Docker Desktop WSL2), INSTALL_LINUX.md, DEPLOY.md (TLS/reverse proxy/public webhook), ENV_REFERENCE.md, TROUBLESHOOTING.md, `docs/IMPLEMENTATION_STATUS.md`. Provide example commands and CPU/GPU Compose profiles.
- Basic production OpenTelemetry/Prometheus log/trace support if budget allows, with field redaction. Error handling, idempotency and retry tests. No hardcoded backend IPs.

Acceptance: fresh clone can bootstrap, tests pass or documented tool limitations, actual integration smoke in CI, setup instructions clear, no secrets or model weights committed. STOP.


---

## 10_HARDWARE.md
# PROMPT 10 — Edge/Linux ARM and PCB handoff readiness, NO custom PCB fabrication yet

Prepare for later deployment on Raspberry Pi CM5 (8GB+ candidate) and RK3588 (8GB+ candidate), with optional ESP32-S3 as audio/control coprocessor. **Do not assume either board can meet latency goals before actual benchmark.** Produce:

- Architecture separation for headless Linux ARM inference daemon, HTTP/WS loopback or IPC, local mic/audio I/O, small LCD frontend mode (PWA or Qt alternative), button control, OTA updates, read-only model bundles and secrets storage.
- ARM64 Docker/build scripts and model conversion checklist (quant INT8/INT4 when supported, ONNX/CT2/whisper.cpp), model size, licensing, memory estimates plus **actual benchmarking instructions** (WER, chrF/COMET where possible, RTF, latency P50/P95, RAM, thermals, watts). Explicit test gate: offline RTF < 1 on target workload with sufficient thermal margin before hardware PCB decision.
- Build a BOM *template* rather than invented current prices; choose interface categories: 2-channel mic/PDM/I2S/USB, codec/DAC, speaker/headphone, LCD/HDMI/MIPI, battery power management, status LEDs, USB-C, Wi-Fi/BLE, power buttons. Caution on battery safety and compute-module carrier high-speed design.
- Design documents for Stage 06 board benchmark → Stage 07 dev-module prototype → Stage 08 custom carrier PCB Rev A. Provide KiCad schematic block diagram specification, pin map placeholders, test points, ERC/DRC and bring-up matrix for manufacturer-ready handoff, no promise of first-revision correctness.
- Offline/cloud failover on device, user privacy and audio retention controls, device provision/secure firmware updates. Compare full offline vs compact local fallback; cloud credentials never embedded in firmware/browser.

Acceptance: downloadable build/benchmark plan, exact measurable go/no-go gates for chip selection, no untested performance promises. STOP.
