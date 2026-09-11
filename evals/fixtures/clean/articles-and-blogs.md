---
channel: articles-and-blogs
min_score: 90
max_findings: 0
---

# What six hours of retries taught me about backoff

On March 3rd our ingest worker spent six hours retrying one malformed row. It
held a Postgres partition the whole time, so the nightly backfill never ran, and
Priya spent her morning draining a queue by hand.

I had written that retry loop two years earlier. I gave it backoff and no
ceiling, because at the time the only failures I had seen were transient network
errors, and those always cleared. A malformed row never clears.

The fix took four lines: cap attempts at three, then move the batch to a
dead-letter table with its payload and the last exception. Deploy time dropped
from 40 minutes to 4, because nothing blocks on the drain step now.

If you write a retry loop this week, give it a ceiling and somewhere to put the
bodies.
