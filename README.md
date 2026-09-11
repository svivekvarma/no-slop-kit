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

### 1. Slack message

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

### 2. Pull request

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

### 3. Email

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

### 4. Code comment

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
| `technical-docs` | Answer first. No em dashes. Say what breaks. |
| `articles-and-blogs` | The closing flourish is deleted, not rewritten. |
| `email` | Ask and deadline in the first two sentences. |
| `messages` | One paragraph. No headings, no bold labels. |
| `social-posts` | Hook line and closing line both go. |
| `social-comments` | Add a fact, a disagreement, or say nothing. |
| `code-comments` | Why, never what. |
| `pull-requests` | Reason, risk, rollback. Not a diff summary. |
| `review-comments` | Say whether it blocks. Propose the change. |

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
