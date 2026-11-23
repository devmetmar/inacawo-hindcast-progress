# Dataset inventory manifests

Lightweight inventory summaries only (day-directory counts, sizes, samples).

- Do **not** store NetCDF payloads or full sensitive logs here.
- `created_at` is never inferred from filesystem mtime.
- Checksums are recorded only when an explicit checksum campaign exists (`checksum_ref`).
