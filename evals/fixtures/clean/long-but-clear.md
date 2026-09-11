---
channel: articles-and-blogs
min_score: 90
max_findings: 0
---

# Why the retry loop had no ceiling

I gave it backoff and no ceiling, because at the time the only failures I had
seen were transient network errors, and those always clear.

On March 3rd our ingest worker spent six hours retrying one malformed row, so
the nightly backfill never ran and Priya drained the queue by hand that morning.

The fix was four lines: cap attempts at three, then move the batch to a
dead-letter table with its payload and the last exception.

Retries stop at three because a malformed row never becomes valid, however long
you wait between attempts.
