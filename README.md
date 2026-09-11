<!-- slop-lint: off -->

# No Slop Kit

Stops your AI assistant writing like an AI assistant.

Slack · PRs · emails · docs · code comments · commits · social

| | |
| --- | --- |
| **Works with** | Claude Code, Codex, Cursor, Gemini CLI, Copilot, Windsurf, or no agent |
| **Detector** | Plain Python. No API key, no network, **zero model tokens** |
| **Costs you** | 698 tokens per session |
| **Install** | One command |

---

## Use cases

### 1. Technical docs

> **You ask:** "Document the timeout setting"

<table>
<tr><th>Without</th><th>With</th></tr>
<tr><td>

```
## Configuration

This section describes the
configuration options that
are available to you.

Our robust configuration
layer empowers you to
seamlessly leverage
environment variables.

It's worth noting that the
`timeout` field plays a vital
role in request handling.

Simply set the value and
you're good to go.
```

</td><td>

```
## Configuration

`INGEST_TIMEOUT` sets the
per-request timeout in
seconds. Default 30.

Set it below 22 and you will
see spurious retries: the
vendor's p99 was 22s in
August 2026.

Values above 120 are rejected
at startup with
`timeout out of range`.

Requires Postgres 14+.
```

</td></tr>
<tr><td><b>0 / 100</b></td><td><b>100 / 100</b></td></tr>
</table>

**Caught:** "this section describes" · "robust", "empowers", "seamlessly", "leverage" · "simply"
**Also caught in docs:** binary contrasts ("this is not a cache, it's a buffer") · paraphrasing the same thing three ways ("the agent" → "the assistant" → "the tool") · marketing register ("out of the box", "under the hood", "blazing fast", "enterprise-grade")
**Delivers:** the default, the real number, the failure mode and its error string

---

### 2. Article or blog post

> **You ask:** "Open a post about retry ceilings"

<table>
<tr><th>Without</th><th>With</th></tr>
<tr><td>

```
In today's fast-paced
engineering landscape,
reliability is paramount.

What nobody tells you is that
most teams get retries wrong.
Here's the thing: backoff
alone isn't enough.
Think about it.

Let me be clear. This isn't
just a technical problem.
It's a mindset problem.

In conclusion, the future of
reliability isn't coming.
It's already here.
```

</td><td>

```
On March 3rd our ingest worker
spent six hours retrying one
malformed row. It held a
Postgres partition the whole
time, so the nightly backfill
never ran, and Priya spent her
morning draining a queue
by hand.

I wrote that retry loop two
years earlier. I gave it
backoff and no ceiling,
because the only failures I
had seen were transient
network errors, and those
always clear. A malformed row
never clears.
```

</td></tr>
<tr><td><b>0 / 100</b></td><td><b>100 / 100</b></td></tr>
</table>

**Caught:** "in today's fast-paced" · "what nobody tells you" · "here's the thing" · "not X, it's Y" · "In conclusion" · the fake-profound last line
**Delivers:** a date, a name, a consequence, and an admission — the closing flourish deleted, not rewritten

---

### 3. Slack message

> **You ask:** "Tell the team the deploy is down"

<table>
<tr><th>Without</th><th>With</th></tr>
<tr><td>

```
Hi team! 👋 Hope everyone's
having a great week!

**Context:** We've been seeing
some issues with the pipeline.

**Impact:** The deploy is
currently down.

**Next steps:** I'll be diving
into the logs.

Let me know if you have
any questions!
```

</td><td>

```
deploy is down, ~15 min.
ingest worker is stuck on a
bad row in the 03-03 file.
draining the queue now, will
post when it clears.
```

</td></tr>
<tr><td><b>10 / 100</b></td><td><b>100 / 100</b></td></tr>
</table>

**Caught:** memo formatting in a chat window · throat-clearing · emoji

---

### 4. Pull request

> **You ask:** "Write the PR description for the retry fix"

<table>
<tr><th>Without</th><th>With</th></tr>
<tr><td>

```
## Summary
This PR refactors the ingest
module to leverage a more
robust retry strategy,
significantly improving
overall reliability.

## Changes
- Updated `worker.py`
- Added comprehensive tests
```

</td><td>

```
One malformed row locked a
Postgres partition for 6h on
Mar 3. Priya drained it by hand.

Batches now stop after 3
attempts and move to
`ingest_dead_letter`.

Risk: table grows if a whole
file is bad. Watch
`ingest_dead_letter_count`.
Revert: INGEST_MAX_ATTEMPTS=0

Fixes #412.
```

</td></tr>
<tr><td><b>0 / 100</b></td><td><b>100 / 100</b></td></tr>
</table>

**Caught:** summarises the diff the reviewer already has · "leverage", "robust" · puffery
**Delivers:** the reason, the risk, the rollback

---

### 5. Email

> **You ask:** "Chase Priya about the PR"

<table>
<tr><th>Without</th><th>With</th></tr>
<tr><td>

```
Hi Priya,

I hope this email finds you
well! I wanted to reach out
regarding the retry budget.

At the end of the day, experts
agree unbounded retries can be
problematic.

Please don't hesitate to
reach out!
```

</td><td>

```
Priya, can you review and
merge #412 by Thursday? If it
misses Friday the March
backfill slips.

The worker retried one bad row
for six hours on March 3rd.
The fix caps attempts at three.
```

</td></tr>
<tr><td><b>0 / 100</b></td><td><b>100 / 100</b></td></tr>
</table>

**Caught:** "hope this finds you well" · "experts agree" · no ask, no deadline
**Delivers:** the ask and the date in sentence one

---

### 6. Code comment

> **You ask:** "Comment this timeout"

<table>
<tr><th>Without</th><th>With</th></tr>
<tr><td>

```python
# This function is responsible
# for handling the timeout
# Note that we simply set
# the timeout to 30 seconds
timeout = 30
```

</td><td>

```python
# 30s: vendor p99 was 22s
# (measured 2026-08). Shorter
# caused spurious retries.
timeout = 30
```

</td></tr>
<tr><td><b>80 / 100</b></td><td><b>100 / 100</b></td></tr>
</table>

**Caught:** narrates the code instead of explaining it
**Delivers:** why, never what

> Every score is from the linter in this repo.
> Reproduce: `python scripts/slop_lint.py draft.md --channel email`

---

## Why it exists

- Slop is rarely pasted into a chat for editing.
- It goes straight into a commit, a runbook, a Slack thread — and gets merged.
- So this runs **when the text is written**, not when someone remembers to check.
- And it knows the channel. Headings are right in a runbook, wrong in Slack.

---

## Why it diverged from Peter Yang's repo

Built on **[petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop)** (MIT).
Peter wrote the slop catalog and the voice-preserving edit rules. Reproduced here
with provenance headers; his copyright stays in [LICENSE](LICENSE).

| | Upstream | Here |
| --- | --- | --- |
| **Runs** | When you paste a draft | Automatically, on files, commits and PRs |
| **Channels** | All prose alike | 9 channels, own rules each |
| **Detection** | The model reads it | Regex first — 0 tokens, runs in CI and git hooks |
| **Tools** | ChatGPT, Codex | + Claude Code, Cursor, Gemini, Copilot, Windsurf, none |

See [NOTICE](NOTICE) for what was copied, what is new, what was left behind.
Not affiliated with or endorsed by Peter Yang.

---

## Install

**Claude Code** — hooks and commands wired automatically:

```sh
/plugin marketplace add svivekvarma/no-slop-kit
/plugin install no-slop-kit
```

**Any other agent:**

```sh
git clone https://github.com/svivekvarma/no-slop-kit && cd no-slop-kit
python tools/install_style.py --target codex --scope user
```

| `--target` | Writes to |
| --- | --- |
| `claude` | `~/.claude/CLAUDE.md` |
| `codex` | `~/.codex/AGENTS.md` |
| `gemini` | `~/.gemini/GEMINI.md` |
| `cursor` | `.cursor/rules/` |
| `copilot` | `.github/copilot-instructions.md` |
| `windsurf` | `.windsurf/rules/` |
| `all` | every one of them |

- Safe on files you already wrote — the block sits between markers.
- `--dry-run` previews · `--uninstall` removes.

**No agent:** `python tools/install_git_hook.py`

---

## Use it

| Command | Does |
| --- | --- |
| `python scripts/slop_lint.py FILE` | Check a file |
| `... --channel email` | Force a channel |
| `... --min-score 70` | Exit 1 if below — for CI |
| `/deslop (draft)` | Model rewrites it |
| `/slop-check FILE` | Audit only, no rewriting |

**Automatic, once installed:**

- Write a `.md` file → linter reports → agent fixes it.
- Run `git commit` or `gh pr create` → message checked before it ships.
- Blocks **once** so it can be reworded. Re-run always goes through.

Opt out with `slop-lint: off` in front matter, or a glob in `.slopignore`.

---

## Channels

| Channel | What changes |
| --- | --- |
| `technical-docs` | Answer first, then explain. No marketing. One name per thing. Say what breaks. |
| `articles-and-blogs` | Cut the performance of insight, keep the story that carries it. |
| `email` | Ask and deadline in the first two sentences. |
| `messages` | One paragraph. No headings, no bold labels. |
| `social-posts` | Hook line and closing line both go. |
| `social-comments` | Add a fact, a disagreement, or say nothing. |
| `code-comments` | Why, never what. |
| `pull-requests` | Reason, risk, rollback. Not a diff summary. |
| `review-comments` | Say whether it blocks. Propose the change. |

---

## Clarity, not brevity

The goal is a reader who understands, not a short draft.

- **Tangled sentences are flagged. Long ones are not.** A 27-word sentence holding one idea reads in one breath. Three clauses and a "which" do not.
- **Causation is protected.** "Because", "so", "which meant" are how a reader follows an argument. Cutting them for punchiness is what makes AI prose read as a list of assertions.
- **Storytelling earns its place in docs**, depending on which doc it is:

| Doc type | Narrative |
| --- | --- |
| Reference (API, flags, config) | None. Field, type, default, limit. |
| How-to / runbook | Only the causation: why this step, what breaks without it. |
| Explanation / ADR | Yes. The problem, what you tried, why it failed, what you chose. |
| Tutorial | Yes. One worked example carried the whole way through. |

> "We ran unbounded retries for two years. On March 3rd one malformed row held a
> partition for six hours. So batches now stop after three attempts."

That arc is not padding. It is the only thing that stops the next person
reverting your fix.

---

## Limits

- Regex catches the mechanical two thirds: fixed phrases, banned words, structure.
- It **cannot** tell if a claim is true, or if a cut line carried your voice.
- That is the model's job, via the skill.
- It does **not** detect whether AI wrote something. Detectors guess, and they are wrong about people.

Proven, not claimed — `known_misses.tsv` holds 18 bad-but-unmatchable lines the
linter must **miss**. If a rule starts catching them, the suite fails.

```
205/205 checks   51/51 upstream examples   0 false positives
```

`python evals/run_evals.py` — free, offline, no key.

---

[CONTRIBUTING](CONTRIBUTING.md) · [CHANGES](CHANGES-FROM-UPSTREAM.md) · [NOTICE](NOTICE) · [PRIVACY](PRIVACY.md) · [EVALS](evals/README.md)

MIT © 2026 Peter Yang and Vivek Siruvuri
