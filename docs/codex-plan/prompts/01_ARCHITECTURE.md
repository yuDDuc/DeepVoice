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
