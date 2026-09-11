---
channel: code-comments
slop-lint: off
---

# Channel: code comments

Inline comments, docstrings, TODOs, type annotations prose.

The rule that decides everything: a comment explains **why**, because the code
already shows **what**. AI-generated comments do the opposite almost every time,
narrating the line below in English.

## Extra rules

- **Delete any comment that restates the code.** `# increment the counter` above `counter += 1` is noise that will go stale.
- **Comment the non-obvious decision.** Why this algorithm, why this magic number, why the obvious approach fails, what broke last time.
- **Link the reason.** A ticket number, an RFC section, a commit SHA, a vendor bug URL. "Workaround for aws/aws-sdk-js#3106" is worth ten sentences.
- **Docstrings: one line saying what it returns, then only what the signature cannot say.** Units, ranges, side effects, raised exceptions, thread safety, what happens on empty input.
- **No section-banner comments.** `# ===== HELPERS =====` is structure the file layout should carry.
- **TODOs name a person and a condition.** `# TODO(vivek): remove once the v2 ingest is default, target Q4` beats `# TODO: refactor this`.
- **No prose ceremony.** No "This function is responsible for", no "Note that", no "Simply". Start with the verb.
- **Say the failure mode.** "Returns None if the row is malformed; callers must handle it" earns its place.

## Channel-specific slop

| Slop | Fix |
| --- | --- |
| `# Loop through the items` | Delete. |
| `# This function calculates the total` above `def calculate_total():` | Delete. |
| `"""Initializes the class."""` on `__init__` | Delete, or say what invariant it establishes. |
| `# Handle the error gracefully` | "Swallow the 404: a missing profile is expected for new users." |
| `# Set timeout to 30` above `timeout = 30` | "30s: the vendor's p99 is 22s (measured 2026-08)." |
| `# Important: do not change this` | Say what breaks if you do. |
| `# Leveraging the robust caching layer for optimal performance` | "Cached because this runs per-row in a 50k-row loop." |
| `# Step 1: ... # Step 2: ...` narrating each line | Delete all of them; one comment on the approach if needed. |

## Keep

Keep the comment that says "this is ugly and here is why we did it anyway".
Keep the swearword in the comment about the vendor API. Keep the long comment
that explains a genuinely subtle invariant. Those are the ones that save the
next person an afternoon.
