---
channel: technical-docs
slop-lint: off
---

# Channel: technical docs

READMEs, API reference, runbooks, ADRs, release notes, internal wikis.

The reader is mid-task and usually mildly annoyed. They want the command, the
field name, or the reason a decision was made. Every sentence that does not help
them finish the task is costing them time.

## Narrative is allowed here, and often required

The rules below are written against marketing and padding, not against
explanation. Do not read them as "make it terse". A doc that is short and
leaves the reader guessing has failed harder than a long one.

Which doc you are writing decides how much narrative earns its place:

| Doc type | Reader is | Narrative |
| --- | --- | --- |
| **Reference** (API, config, flags) | Looking one thing up | None. Field, type, default, limit. |
| **How-to** (runbook, task guide) | Mid-task, often at 2am | Only the causation: why this step, what breaks without it. |
| **Explanation** (architecture, ADR, concept) | Trying to understand | Yes. The problem, what you tried, why it failed, what you chose. |
| **Tutorial** (getting started) | Learning, no context yet | Yes. One worked example carried the whole way through. |

In explanation and tutorial docs, tell the story: "We ran unbounded retries for
two years. On March 3rd one malformed row held a partition for six hours. So
batches now stop after three attempts." That arc is not padding. It is the only
thing that stops the next person reverting your fix.

What makes a doc hard to read is rarely length. It is a sentence carrying three
ideas, an abstract noun where a verb belongs, and a missing "because".

- **One idea per sentence.** If you need three commas and a "which" to hold it together, it is two sentences.
- **Keep the "because".** "Retries stop at three because a malformed row never becomes valid" beats "the retry limit is three". The reason is what the reader needs to decide whether your rule applies to them.
- **Lead each section with the answer, then explain.** Front-loading is not the same as omitting.

## Extra rules

- **Answer the question in the first sentence.** A runbook section starts with the command, not with what the section will cover. Cut "This section describes..." and "In this guide we will...".
- **Zero em dashes.** Docs get scanned, not read aloud. Use a period or a colon.
- **Version and date every claim that can rot.** "Requires Node 20+" beats "requires a modern Node". "As of 2.4" beats "currently".
- **Name the actor in every instruction.** "The scheduler retries" beats "retries are attempted".
- **Show the real command and the real output.** Fake output in a code block is worse than no output.
- **One concept per heading, and no heading over a two-sentence section.** If a section is two sentences, fold it into the parent.
- **Say what breaks.** Docs that only describe the happy path get a support ticket. Name the failure mode and the error string the reader will actually see.
- **No marketing in reference material.** A field description is not a place for "powerful" or "flexible". Say what the field does and what its default is.
- **Name the thing once and keep naming it that.** Rotating terms for variety ("the agent", then "the assistant", then "the tool") is worse in reference material than anywhere else: a reader scanning for one term cannot tell whether the other two mean the same thing. Pick the word and repeat it.
- **State it, do not sell it.** "Out of the box", "under the hood", "blazing fast", "enterprise-grade", "rock solid", "future-proof", "batteries included". These have no technical meaning. Replace each with the number, the default, or the limit.
- **No binary contrasts.** "This is not a cache. It's a write-through buffer." Just say what it is: "A write-through buffer. Writes go to Postgres and the cache in the same transaction."
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
| "It works out of the box." | "No configuration is required. The defaults are in `config/default.yml`." |
| "Under the hood, it does the heavy lifting." | Say what it does: "It batches writes in groups of 500." |
| "A blazing fast, enterprise-grade pipeline." | "Ingests 50k rows/sec on 4 vCPU (measured 2026-08)." |
| "The agent reads the queue. The assistant scores it." | Call it the agent both times. |
| "This is not a cache. It's a buffer." | "A write-through buffer." |

## Keep

Keep the warnings, the "we tried X and it did not work" notes, and the blunt
admissions of known bugs. Those are the most valuable sentences in most internal
docs, and they are the first thing a polishing pass deletes.

Keep the worked example that runs through the whole page. Keep the incident that
explains why the limit is three and not five. Keep a long sentence when it holds
one idea and reads in one breath. Cutting those does not make a doc cleaner, it
makes it a reference page pretending to be an explanation.
