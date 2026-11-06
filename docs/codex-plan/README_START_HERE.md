# AVRT Studio — Codex prompt pack

**Product:** Adaptive Verified Real-time Translator; EN ⇄ VI, speech-to-speech, live captions, model plug-in, monitoring, billing, cloud/offline hybrid. This pack is a sequence of **instructions to Codex**, not a completed app.

## Use

1. Create or open a new Git repository; copy this pack into `docs/codex-plan/`. Keep `.env.example` at repo root as the canonical env template.
2. In Codex, send `prompts/00_MASTER.md`, or paste it, and provide the repo location. It instructs Codex to read `reference/SYSTEM_REQUIREMENTS.md`, `reference/ENV_CONTRACT.md` and `.env.example`.
3. Send **one phase prompt at a time, in numeric order**. After every phase, require Codex to run tests, update `docs/IMPLEMENTATION_STATUS.md`, and stop. Only proceed after reviewing the acceptance criteria.
4. Configure `.env` locally from `.env.example`. Never commit `.env`, payment keys, HF tokens, audio recordings or model weights. A `mock` provider must allow functional demo without real credentials or model downloads.
5. For real money, register payment accounts and receive provider webhooks over publicly reachable HTTPS. Do not treat a generated VietQR image as receipt confirmation.

## Phases

| Prompt | Scope | Exit result |
|---|---|---|
| 00 | Master contract | Operating constraints + planned work |
| 01 | Architecture, ERD, access/data flows | Mermaid diagrams, API/WS contract, ADRs |
| 02 | Monorepo, Mongo replica set, Redis, infra baseline | One-command CPU dev environment + smoke tests |
| 03 | Model adapters and Hugging Face/local loading | Editable model registry, preflight, download/progress |
| 04 | Streaming ASR/MT/verification/TTS + features | Bidirectional live translation, deterministic state machine |
| 05 | CPU/GPU + inference metrics | Realtime monitoring dashboard contract and metrics |
| 06 | Auth, RBAC, persistence | Sign-up/in/out, session protections, saved history |
| 07 | Billing, VietQR/payOS, SePay, Google Pay gateway-ready | Mock checkout end-to-end, signature/idempotency tests |
| 08 | Next.js frontend | Real dashboards, settings, live translation, checkout |
| 09 | Deployment/CI/security/performance | Reliable CPU/GPU profiles, CI, reproducible tests |
| 10 | Hardware handoff / ARM readiness | Edge strategy and board validation plan |

**Recommended first delivery:** phases 00–03 + 06 + 08 for a UI/mock demonstration; then 04–05 for live inference; then 07, 09, 10. For code dependencies, Codex may add a thin placeholder earlier but cannot claim a feature is complete before its phase.

## Important technical caveats

- HF Hub model downloads (`hf_hub`) and remote HF Inference (`hf_remote`) are separate strategies. Weight files normally must download/cache and load for local runtime; streaming **output chunks** and **weights** are different concepts.
- Google Pay is a wallet interface that needs a supported payment processor; it is not interchangeable with Vietnamese bank transfer QR.
- MongoDB multi-document transactions require a replica set/sharded cluster; default Docker dev profile should initialize a single-node replica set to test transactions, and document its non-HA status.
- NVIDIA GPU container support requires supported drivers/toolkit. CPU-only path must work without NVML/CUDA.
- Shape settings may be edited in `.env`, but a compatible adapter and validated model architecture are still required; never silently reshape weights or tensors.
- All initial prices/credit ratios are configurable examples, not production policy or promises.

## Diagrams and permissions supplied as starting design

The `reference/diagrams/*.mmd` files and `reference/ACCESS_MATRIX.md` are **editable starter designs** accompanying the phase-01 instructions. Codex should validate and revise them to match implemented collections and routes; they are not evidence that the app has been built.
