---
channel: technical-docs
min_score: 90
max_findings: 0
---

# Compatibility

The adapter is a drop-in replacement for the v1 client. Deploy the cloud-native
build with `helm install ingest ./chart`.

The library is not production ready. The API may change before 1.0, and the
`replay` signature already changed once in 0.7.

Pass `--strict` to fail the build on any warning. The default is `--no-strict`.

The worker retries three times, then dead-letters the batch with its payload and
the last exception.
