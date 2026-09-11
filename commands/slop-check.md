---
description: Audit a draft or file for AI-slop patterns and report findings without rewriting anything.
slop-lint: off
---

Audit the target below for AI-slop patterns. Report only. Do not rewrite it.

First run the linter for the free mechanical pass. If the target is a file:

```sh
python scripts/slop_lint.py <path> --format text
```

If the target is pasted text, write it to a temporary file and lint that, or
skip the linter and read the patterns yourself.

Then read `skills/no-ai-slop/SKILL.md` and the matching channel file in
`skills/no-ai-slop/channels/`, and find the patterns the linter cannot see:
synonym cycling, portability failures, structure that does not serve the reader,
detail smoothed into generic importance, and voice that has been flattened.

Report as a list. For each finding give the pattern name, the quoted line, and
the fix in a few words. Group the linter's findings and your own together and
say which came from where.

Do not score the writing. Do not guess whether AI wrote it; named patterns are
evidence the user can check, and detectors guess. Offer to edit the draft after.

$ARGUMENTS
