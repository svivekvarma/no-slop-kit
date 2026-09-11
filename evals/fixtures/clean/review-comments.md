---
channel: review-comments
min_score: 90
max_findings: 0
---

blocking: this 500s when `rows` is empty, because `rows[0]` runs before the
length check. Move the guard above line 42.

nit: three retries and not five, why? Worth a comment with the reason.
