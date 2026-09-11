---
channel: review-comments
slop-lint: off
---

# Channel: review comments

Code review comments, PR replies, review summaries.

A review comment is read by a person whose work is being criticised, usually
while they are busy. It needs to be specific, actionable, and clear about
whether it blocks. Slop here is the padded, hedged, faux-collaborative comment
that takes four sentences to not quite ask for a change.

## Extra rules

- **Say whether it blocks.** Prefix with `blocking:`, `non-blocking:`, `question:` or `nit:`. A reviewer who does not say this makes the author guess.
- **One comment, one issue, on the line it concerns.** Do not bundle five points into a summary paragraph.
- **Propose the change, do not gesture at it.** Paste the two lines you would write instead.
- **Say the consequence.** "This will 500 when `rows` is empty" beats "might want to handle the empty case".
- **Cut the hedging stack.** "I might be missing something here, but I was wondering whether it could perhaps make sense to..." is one sentence of content in thirty words.
- **Ask a real question when you do not know.** "Why three retries and not five?" is a fine comment.
- **Under 60 words per comment.** No headings, no bullets for a single point.
- **Approve plainly.** "Approved" or "LGTM, one nit" is enough. An approval does not need a summary of the PR.

## Channel-specific slop

| Slop | Fix |
| --- | --- |
| "Great work on this! Just a few minor thoughts..." | "3 nits, 1 blocking." |
| "I might be missing something, but could we perhaps consider..." | "Why not X? Y breaks when the list is empty." |
| "It would be nice to have some tests here." | "blocking: needs a test for the empty-rows path." |
| "Consider refactoring this for better readability." | Paste the version you would write. |
| "This looks good overall, however I do have some concerns." | Name the concern in the first clause. |
| "Nice use of the strategy pattern here!" | Delete, or say what it made easier. |
| "As per best practices, we should..." | Say why it matters here. |
| A closing "Thanks for your hard work on this!" | Delete. |

## Keep

Keep "I do not understand this function". Keep "this is my fault, I wrote the
original". Keep the short blunt "no, this needs to change before merge". Keep
praise when it names a specific decision you thought was smart.
