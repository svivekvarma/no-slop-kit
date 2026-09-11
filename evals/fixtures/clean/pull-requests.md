---
channel: pull-requests
min_score: 90
max_findings: 0
---

Add retry budget to ingest worker

One malformed row locked a partition for six hours on March 3rd. The worker
retried the same batch forever, so the on-call engineer drained the queue by
hand.

Batches now stop after three attempts and move to `ingest_dead_letter`.

Risk: the dead-letter table grows if a whole file is malformed. Watch
`ingest_dead_letter_count` after deploy. Revert by setting `INGEST_MAX_ATTEMPTS=0`.

Did not change the replay path. Ran `pytest tests/ingest`, 41 passed.

Fixes #412.
