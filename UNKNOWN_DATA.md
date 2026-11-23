# Remaining UNKNOWN / NOT_RECORDED fields

Inventory scan `2026-11-23` filled every field that could be evidenced without inventing scientific dates, owners, checksums, or acceptance.

## Filled from evidence

| Field | Source |
|-------|--------|
| `size_bytes` / `size_human` | `du -sb` on dataset roots (except `cawo_hindcast_run` still pending) |
| `file_count` | Day-directory counts (CLS products / run) or `find` file count (internal) |
| `manifest_ref` | `data/manifests/inventory_scan_20261123.json` |
| `last_inventory_scan` | `2026-11-23` |
| `period_coverage` (internal input) | Dated era5/glorys/f markers on disk |
| `validation_status` | Set to `NOT_VALIDATED` (no validation records) instead of vague `UNKNOWN` |
| `lifecycle_status=INCOMPLETE` | `cawo_hindcast_run` (gap 1997–2001); internal input (sparse samples) |

## Intentionally still UNKNOWN / null

These **must not** be fabricated:

| Field | Why still unknown |
|-------|-------------------|
| `created_at` / `created_at_provenance` | No scientific creation provenance; filesystem mtime is not used |
| `verified_at` | No checksum / integrity campaign completed |
| `accepted_at` | No human acceptance recorded |
| `owner` | Team roster still placeholders (`OPEN_QUESTIONS` Q4) |
| `checksum_ref` | No checksum manifests produced |
| `integrity_status` | Remains `NOT_VERIFIED` until a defined integrity campaign |
| Task `due_date` | None assigned |
| `cawo_hindcast_run` size | `du -sb` still running / incomplete at last update |

## How to clear remaining unknowns

1. **created_at** — only with documented provenance (production logs / delivery notes), never mtime alone.
2. **checksum_ref / verified_at** — run an agreed checksum or byte-inventory campaign; store digest list path in-repo.
3. **owner** — replace `data/team.yaml` placeholders, then assign member IDs.
4. **accepted_at** — after scientific validation + human acceptance workflow.
5. **run size** — finish `du -sb $SCRATCH_HISTORICAL/data/cawo_hindcast_run` and update the dataset YAML.
