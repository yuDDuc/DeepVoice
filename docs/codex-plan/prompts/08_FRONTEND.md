# PROMPT 08 — Complete Next.js FE integrated with real BE

Implement a responsive, Vietnamese-first UI with dark/light theme and accessibility. Pages:
`/` landing/value; `/auth/login`, `/auth/register`, `/auth/forgot`; `/app/translate/live` two-way mic, live waveform, partial/confirmed/corrected EN/VI dual transcript, talk button, speaker badges, provider/local state, subtitles+TTS controls, verification warnings; `/app/translate/upload`; `/app/history` session list/detail/export/delete; `/app/models` active role/model/source/revision/health/validate/download status with admin controls gated; `/app/monitor` realtime CPU/GPU/VRAM/RAM/latency/P50/P95 + no-NVML fallback; `/app/billing` plans, balance, buy credits, VietQR modal with amount/account/description/copy, status polling/socket, invoice/history; `/app/settings` privacy, audio retention, speaker memory, profile; `/admin` protected controls, audit and reconciliation.

All UI must use typed real API/WS clients with mocked BE **only in explicit mock mode**. No hardcoded empty business success. Source of truth for role model settings in backend env; UI may request permitted runtime selection but not expose secrets. Handle mic permission failure, mobile layout, reconnect, slower-than-realtime warnings, provider fallback, QR payment pending, token expiry, offline network.

For metrics use genuinely live data or clear 'unavailable'. For payments use server-provided QR/link + merchant metadata; Google Pay shows only when `capabilities.google_pay.enabled=true` from server. Screenshots/Playwright tests at 1440px and 375px, key flows. Simple elegant SaaS aesthetic; meaningful loading/skeleton/error and empty states, no generated static 'fake' prices in production.

Acceptance: end-to-end sign-in → mock live translate → monitor → save/export → mock checkout → credit balance view; two-account authorization negative test; responsive screenshots and FE tests. STOP.
