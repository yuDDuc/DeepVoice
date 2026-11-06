# MP3 upload design

## Goal

Allow users to select MP3 files in the audio upload page while preserving the
existing WAV upload behavior and backend audio contract.

## Design

- Keep the existing upload endpoint and its WAV PCM16 mono input contract.
- In the browser, decode selected MP3 files with the Web Audio API, convert the
  decoded audio to mono PCM16 WAV, and submit that WAV through the existing
  upload flow.
- Submit WAV selections unchanged.
- Expand the file picker to accept MP3 and update the page copy to explain that
  MP3 is converted in the browser.
- Do not add a backend decoder or dependency. Keep server-side size, format,
  and sample-rate validation unchanged. Give uploads an independent duration
  limit of 60 seconds without changing the existing streaming buffer limit.
- If browser decoding fails, report a clear user-facing error and do not submit
  the file.

## Validation

- Verify MP3 selection is accepted and conversion creates a valid WAV upload.
- Verify conversion errors are reported without submitting a request.
- Keep existing WAV upload behavior and invalid-file rejection covered by tests.
