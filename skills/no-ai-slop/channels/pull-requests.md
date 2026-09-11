---
channel: pull-requests
slop-lint: off
---

# Channel: pull requests and commits

Commit messages, PR titles, PR descriptions.

The reader is a reviewer deciding whether to approve, or an engineer six months
from now running `git log` on a line that just broke. Both want the same thing:
why this change exists and what to watch out for. AI-written PR bodies reliably
produce a beautiful summary of the diff, which is the one thing the reader can
already see.

## Extra rules

- **The body says why. The diff says what.** Do not enumerate the files you changed; the reviewer has the file list.
- **Commit subject: imperative mood, under 72 characters, no trailing period.** "Add retry budget to ingest worker", not "Added retry budget" or "This commit adds...".
- **First line of the PR body is the reason.** "One malformed row locked a partition for 6 hours on March 3rd." Then what you did about it.
- **Name the risk and the rollback.** What could break, what to watch after deploy, how to revert. This is the most valuable paragraph in a PR body and the one AI never writes.
- **Say what you did not do.** Out-of-scope items and known gaps, so the reviewer does not hunt for them.
- **Link the ticket and the incident.** Not "resolves the issue".
- **No emoji, no headings in a short PR, no bold labels.** A three-line PR does not need a `## Summary` section.
- **Test evidence, not test claims.** "Ran `pytest tests/ingest` (41 passed)" beats "added comprehensive tests".
- **No em dashes.**

## Channel-specific slop

| Slop | Fix |
| --- | --- |
| "This PR refactors the ingest module to improve maintainability." | "Ingest retried forever; one bad row locked a partition for 6h." |
| "## Summary" / "## Changes" / "## Testing" on a 10-line diff | Three sentences of prose. |
| "- Updated `worker.py` - Updated `config.py`" | Delete. That is the file list. |
| "Comprehensive test coverage has been added." | "Added `test_dead_letter_on_third_failure`; `pytest tests/ingest` 41 passed." |
| "This change enhances the robustness of the system." | "Failed batches now stop after 3 attempts instead of retrying forever." |
| "Various improvements and bug fixes" as a commit subject | One subject per change, or say which bug. |
| "Fixes #412, showcasing our commitment to reliability." | "Fixes #412." |
| "No breaking changes." with nothing else | Say what you checked to know that. |
| "LGTM, merging." as the description | Write one sentence on why it exists. |

## Keep

Keep "I am not sure this is the right fix, but it stops the bleeding". Keep the
note that you copied an approach from another service. Keep the paragraph
admitting you do not understand why the old code worked. Reviewers act on those
lines.
