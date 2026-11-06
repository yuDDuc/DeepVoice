# PROMPT 10 — Edge/Linux ARM and PCB handoff readiness, NO custom PCB fabrication yet

Prepare for later deployment on Raspberry Pi CM5 (8GB+ candidate) and RK3588 (8GB+ candidate), with optional ESP32-S3 as audio/control coprocessor. **Do not assume either board can meet latency goals before actual benchmark.** Produce:

- Architecture separation for headless Linux ARM inference daemon, HTTP/WS loopback or IPC, local mic/audio I/O, small LCD frontend mode (PWA or Qt alternative), button control, OTA updates, read-only model bundles and secrets storage.
- ARM64 Docker/build scripts and model conversion checklist (quant INT8/INT4 when supported, ONNX/CT2/whisper.cpp), model size, licensing, memory estimates plus **actual benchmarking instructions** (WER, chrF/COMET where possible, RTF, latency P50/P95, RAM, thermals, watts). Explicit test gate: offline RTF < 1 on target workload with sufficient thermal margin before hardware PCB decision.
- Build a BOM *template* rather than invented current prices; choose interface categories: 2-channel mic/PDM/I2S/USB, codec/DAC, speaker/headphone, LCD/HDMI/MIPI, battery power management, status LEDs, USB-C, Wi-Fi/BLE, power buttons. Caution on battery safety and compute-module carrier high-speed design.
- Design documents for Stage 06 board benchmark → Stage 07 dev-module prototype → Stage 08 custom carrier PCB Rev A. Provide KiCad schematic block diagram specification, pin map placeholders, test points, ERC/DRC and bring-up matrix for manufacturer-ready handoff, no promise of first-revision correctness.
- Offline/cloud failover on device, user privacy and audio retention controls, device provision/secure firmware updates. Compare full offline vs compact local fallback; cloud credentials never embedded in firmware/browser.

Acceptance: downloadable build/benchmark plan, exact measurable go/no-go gates for chip selection, no untested performance promises. STOP.
