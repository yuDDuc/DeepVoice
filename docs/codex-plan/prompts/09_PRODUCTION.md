# PROMPT 09 — Docker, test, security, release and observability hardening

Make repository reproducible and production-minded without claiming hardware/payment certification:

- Compose CPU startup must work with no GPU; optional `compose.gpu.yml` verified against NVIDIA Container Toolkit. No HF model downloads in Docker build; named persistent cache. Mongo dev replica set bootstrapped deterministically; production docs require appropriate multi-node replica set, secure credentials, backups and restore test. Redis health, inference worker queue and WS ingress. Limit CPU/RAM and number of concurrent streams via env.
- Security audit: dependency scan/lock, secrets scanning, origin checks, cookie flags for prod, CSRF, WebSocket ticket, per-route RBAC, request caps and content-type validation, path traversal for local model directories, no arbitrary `trust_remote_code`/pickle loads by default, streaming quotas, PII redaction. Verify privacy and consent for raw audio and speaker profiles.
- Integration/e2e test matrix: mock CPU, local fixture, optional HF_HUB, optional HF_REMOTE, CUDA available, disconnection/reconnect, dynamic model swap, no Internet, partial correction, high-risk negation, concurrent users, duplicate webhook, bad signature, transaction rollback, frontend billing flow. Load test realistic audio chunks; document P50/P95/RTF and RAM/VRAM actually measured, along with machine specs.
- CI workflow: lint/typecheck/unit/integration/e2e, skip gated external tests clearly. Documentation: INSTALL_WINDOWS.md (Docker Desktop WSL2), INSTALL_LINUX.md, DEPLOY.md (TLS/reverse proxy/public webhook), ENV_REFERENCE.md, TROUBLESHOOTING.md, `docs/IMPLEMENTATION_STATUS.md`. Provide example commands and CPU/GPU Compose profiles.
- Basic production OpenTelemetry/Prometheus log/trace support if budget allows, with field redaction. Error handling, idempotency and retry tests. No hardcoded backend IPs.

Acceptance: fresh clone can bootstrap, tests pass or documented tool limitations, actual integration smoke in CI, setup instructions clear, no secrets or model weights committed. STOP.
