---
channel: technical-docs
slop-lint: off
---

# Channel: technical docs

READMEs, API reference, runbooks, ADRs, release notes, internal wikis.

The reader is mid-task and usually mildly annoyed. They want the command, the
field name, or the reason a decision was made. Every sentence that does not help
them finish the task is costing them time.

## Extra rules

- **Answer the question in the first sentence.** A runbook section starts with the command, not with what the section will cover. Cut "This section describes..." and "In this guide we will...".
- **Zero em dashes.** Docs get scanned, not read aloud. Use a period or a colon.
- **Version and date every claim that can rot.** "Requires Node 20+" beats "requires a modern Node". "As of 2.4" beats "currently".
- **Name the actor in every instruction.** "The scheduler retries" beats "retries are attempted".
- **Show the real command and the real output.** Fake output in a code block is worse than no output.
- **One concept per heading, and no heading over a two-sentence section.** If a section is two sentences, fold it into the parent.
- **Say what breaks.** Docs that only describe the happy path get a support ticket. Name the failure mode and the error string the reader will actually see.
- **No marketing in reference material.** A field description is not a place for "powerful" or "flexible". Say what the field does and what its default is.
- **Tables for facts, prose for reasoning.** If every row is `name / type / default`, use a table. If it needs a "because", use a sentence.

## Channel-specific slop

| Slop | Fix |
| --- | --- |
| "This section describes the configuration options." | Delete. The heading said that. |
| "Simply run the command." | "Run `bin/deploy`." Nothing is simple to the person reading a runbook at 2am. |
| "Robust error handling is provided." | "Failed batches retry three times, then move to `ingest_dead_letter`." |
| "Please note that the API may return an error." | "The API returns 429 when you exceed 100 requests a minute." |
| "For more information, see the documentation." | Link the exact page. |
| "This powerful feature allows you to..." | "This flag lets you..." or just describe the flag. |
| "Best practices dictate that..." | Say who recommends it and why, or state the rule directly. |

## Keep

Keep the warnings, the "we tried X and it did not work" notes, and the blunt
admissions of known bugs. Those are the most valuable sentences in most internal
docs, and they are the first thing a polishing pass deletes.
