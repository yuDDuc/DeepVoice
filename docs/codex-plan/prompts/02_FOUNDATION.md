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
