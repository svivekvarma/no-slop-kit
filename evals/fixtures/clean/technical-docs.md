---
channel: technical-docs
min_score: 90
max_findings: 0
---

# Retry budget

Each batch gets three attempts with backoff at 1s, 4s and 16s. After the third
failure the batch moves to `ingest_dead_letter` with the original payload and
the last exception.

Requires Postgres 14 or newer. The `ingest_dead_letter` table must exist before
the worker starts, or it exits with `relation does not exist`.

To replay a batch, run `bin/replay --batch-id <id>`. Replay is idempotent.
