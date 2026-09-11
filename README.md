<!-- slop-lint: off -->

# No Slop Kit

Catches AI-slop patterns in prose across nine channels, then has your coding
agent fix them. Works in Claude Code, Codex, Cursor, Gemini CLI, Copilot,
Windsurf, or with no agent at all.

The detector is a regex linter in the standard library. It costs zero model
tokens, runs offline, and needs no API key.

```sh
python scripts/slop_lint.py docs/runbook.md
```

```
docs/runbook.md  [technical-docs]  score 38/100 (slop)  212 words
  docs/runbook.md:7  [slop] superficial-analysis - Superficial -ing analysis
      "...adds file search, highlighting the team's commitment t..."
      fix: Replace with the concrete consequence.
  docs/runbook.md:12  [slop] importance-puffery - Importance puffery
      "...worth noting that this marks a pivotal moment for the compa..."
      fix: State the fact; let the reader judge.
```

## Credit

This project is derived from [**petergyang/no-ai-slop**](https://github.com/petergyang/no-ai-slop)
by **Peter Yang**, MIT licensed. Peter wrote the thing that matters most here:
the catalog of slop patterns, the words-to-cut lists, and the editing
principles that keep an edit from flattening the writer's voice. Those are
reproduced in `skills/no-ai-slop/SKILL.md` and `eval.md`, with provenance
headers on both files.

The original copyright notice is kept verbatim in [`LICENSE`](LICENSE) beside
this project's own, as MIT requires. [`NOTICE`](NOTICE) gives a file-by-file
account of what came from upstream, what is new, and what was deliberately not
copied. This project is not affiliated with or endorsed by Peter Yang. If you
want the original skill unmodified, install it from
[his repo](https://github.com/petergyang/no-ai-slop).

## Why this exists

Upstream is a skill you invoke. You paste a draft, it edits, you copy the
result back. That works, and for a newsletter draft it is the right shape.

Three things it does not do, which is what this repo adds.

**It waits to be asked.** Most slop is never pasted into a chat window. It goes
straight into a commit message, a PR body, a runbook, a Slack message. By the
time anyone thinks to run an editor over it, it is merged. So the linter is
wired to hooks instead: it runs on every prose file your agent writes and on
every `git commit` and `gh pr create` before the text is published.

**Slop is channel-specific and it treats all prose the same.** A 900-word
document with headings is right for a runbook and wrong for a Slack message. A
PR body that summarises the diff is useless, because the reviewer has the diff.
A code comment that narrates the line below it is worse than no comment. Nine
channel files encode what counts as slop where, and the linter changes which
rules apply and how hard.

**Judging prose needs a model, and a model is not always worth spending.**
Roughly two thirds of real slop is mechanical: fixed phrases, banned words,
structural tells. Regex catches those for nothing. That leaves the model free
for the part that genuinely needs judgement, and lets the check run in CI and
in a git hook where no model is available.

There is a fourth reason, smaller but the one you notice daily: a style section
in your agent's instruction file stops the slop being generated in the first
place. Cheaper than editing it out afterwards.

## What it costs

Measured, not estimated away. Regenerate with `python tools/token_report.py`.

| What | Tokens | When it loads |
| --- | ---: | --- |
| Style block | **698** | Every session, once installed |
| `no-slop` SKILL.md | 3,765 | Only when the skill runs |
| `eval.md` | 1,370 | Only when the skill self-checks |
| One channel file | 736 | Only when the skill runs, one of nine |
| `no-slop-setup` SKILL.md | 915 | Only when installing |
| `/deslop`, `/slop-check` | 217, 306 | Only when invoked |
| Hook finding report | ~285 | Only on a write that has slop in it |

**The always-on cost is 698 tokens per session.** That is the style block, and
it is the only thing that loads unconditionally. Channel files load one at a
time and only when the skill is actually editing, which is why they are not
`@`-imported into your instruction file.

The linter costs **zero** model tokens. It is Python in a subprocess. Only its
findings reach the model, only for a file that has slop in it, capped at eight
findings, and only once per version of the file.

Counts are estimated at 3.7 characters per token. Run
`python tools/token_report.py --exact` with an API key for real counts from
`count_tokens`.

### Is 698 tokens worth it

It replaces the correction you would otherwise type. One "rewrite that without
the marketing voice" round trip costs more than 698 tokens: your message, the
model re-reading the draft, and a second full draft. The block pays for itself
the first time it prevents one of those, and it prevents them every session.

## Install

### As a Claude Code plugin

```sh
/plugin marketplace add svivekvarma/no-slop-kit
/plugin install no-slop-kit
```

This wires both hooks and registers `/no-slop`, `/no-slop-setup`, `/deslop`
and `/slop-check`.

### As a skill for any agent

Clone it and point your agent at the rules:

```sh
git clone https://github.com/svivekvarma/no-slop-kit
cd no-slop-kit
python tools/install_style.py --list
```

Then install the style block where your tool reads it:

```sh
python tools/install_style.py --target claude  --scope user     # ~/.claude/CLAUDE.md
python tools/install_style.py --target codex   --scope user     # ~/.codex/AGENTS.md
python tools/install_style.py --target gemini  --scope user     # ~/.gemini/GEMINI.md
python tools/install_style.py --target cursor  --scope project  # .cursor/rules/
python tools/install_style.py --target copilot --scope project  # .github/
python tools/install_style.py --target all     --scope project  # everything, committed
```

The block sits between `<!-- no-slop-kit:start -->` and `<!-- no-slop-kit:end -->`.
Re-running replaces it in place and leaves the rest of your file alone, so it
is safe on an instruction file you have already written by hand. `--uninstall`
takes it back out. `--dry-run` shows you the paths first.

Inside Claude Code you can also just ask: *"set up no-slop at user level"*, and
the `no-slop-setup` skill runs the right command.

### With no agent at all

```sh
python tools/install_git_hook.py       # lints commit messages, warns only
NO_SLOP_STRICT=1 git commit            # or make it reject
```

`.github/workflows/slop-lint.yml` runs the linter over prose changed in a PR
and runs the eval suite. It reports and does not fail the build, because a red
X on wording teaches people to ignore CI. Swap in `--min-score 60` if your team
wants it enforced.

## Use it

### The linter

```sh
python scripts/slop_lint.py DRAFT.md                      # channel inferred from path
python scripts/slop_lint.py DRAFT.md --channel email
python scripts/slop_lint.py *.md --format json
python scripts/slop_lint.py DRAFT.md --min-score 70        # exit 1 if below
cat draft.txt | python scripts/slop_lint.py -
python scripts/slop_lint.py --list-channels
```

Three severities. `slop` is a signature pattern and almost always worth fixing.
`likely` usually is. `check` needs your judgement and is often fine as written.
The score is a rough signal, not a measure of quality. Do not edit a line only
to clear a finding.

### The skill

```
/no-slop (your draft)              edit it, preserving your voice
/no-slop is this slop? (draft)     name the patterns, rewrite nothing
/deslop (draft)                    same as the first, as a command
/slop-check path/to/file.md        audit a file, linter plus judgement
```

### The hooks

Once installed, two things happen without you asking.

**After any write to a `.md`, `.mdx` or `.txt` file**, the linter runs and hands
the agent its findings, which the agent fixes in place. It reports once per
version of the file, so fixing it never triggers a second round.

**Before `git commit`, `gh pr create`, `gh issue create` and `gh pr comment`**,
the linter reads the message text out of the command. If it finds signature
slop it blocks once with the findings so the agent can reword; re-running the
same command is allowed through, so it can never wedge you.

To exempt a file, add `slop-lint: off` to its front matter or a glob to
`.slopignore`.

## Channels

| Channel | Covers | What changes |
| --- | --- | --- |
| `technical-docs` | READMEs, API docs, runbooks, ADRs | No em dashes, answer first, say what breaks |
| `articles-and-blogs` | Articles, blog posts, newsletters | Kicker and recap deleted, not rewritten |
| `email` | Work email, outreach, replies | Ask and deadline in the first two sentences |
| `messages` | Slack, Teams, Discord, DMs | One paragraph, no headings or bold labels |
| `social-posts` | LinkedIn, X, Threads, Bluesky | Hook line and closing line both go |
| `social-comments` | Replies and comments | Add a fact, a disagreement or a question |
| `code-comments` | Inline comments, docstrings | Why, never what |
| `pull-requests` | Commits, PR titles and bodies | Reason, risk and rollback, not a diff summary |
| `review-comments` | Review comments and replies | Say whether it blocks; propose the change |

The channel is inferred from the file path, or set with `--channel`.

## Tests

Two suites. The first is offline and free, the second calls a model.

```sh
python evals/run_evals.py            # 199 checks, no credentials, no cost
python evals/run_agent_evals.py      # 26 calls, ~$0.05 on Haiku 4.5
```

The offline suite measures three things that matter:

```
checks        199/199 passed
recall        51/51 upstream examples (100%) over 17 patterns
known misses  18/18 left to the model
false pos.    0 in 419 words (0.00 per 1000)
```

**Recall is measured against the upstream author's own example sentences**, not
against examples written here, so the linter is scored on a definition of slop
it was not tuned on.

**Known misses are asserted to be missed.** `evals/fixtures/known_misses.tsv`
is 18 lines of genuinely bad writing with no mechanical tell: abstraction,
portability failures, smoothed-over detail, unverifiable claims. The suite fails
if the regex starts catching them, because that would mean a rule got too broad.
This is what keeps the claim "the model does the rest" honest.

**False positives are the number that decides whether anyone keeps the linter
on.** The clean corpus is human-written prose that must produce zero findings.

The agent suite is the end-to-end one: it asks a real model to write a PR body,
a Slack message, a runbook section and ten other things, once without the style
block and once with it, and lints both.

A case passes when the styled output has **zero signature findings**, keeps
every fact the prompt supplied, and clears a score floor of 60. Signature
findings are the severity-3 patterns nobody defends. The fact check is what
stops a model from scoring well by deleting content.

Per-case score deltas are reported but not gated, and that is deliberate. At one
sample per condition, run-to-run variance is larger than the effect: across
three full runs the same Slack case scored 70/70, then 100/70, then 70/100
without any change to the prompt or the rules. Gating on that would be fitting
to noise. What is gated in aggregate is that the styled runs produce no more
signature slop than the baseline, and that the styled mean does not fall far
below it. Use `--repeat 3` when a number matters.

```sh
python evals/run_agent_evals.py --estimate                       # price it first
python evals/run_agent_evals.py --repeat 3                       # average 3 samples
python evals/run_agent_evals.py --models claude-haiku-4-5,claude-sonnet-5
python evals/run_agent_evals.py --channels messages,pull-requests
python evals/run_agent_evals.py --backend codex                  # or claude
```

It defaults to the Anthropic API with Haiku 4.5, which is about five cents a
run. The `claude` and `codex` CLI backends reload their whole agent harness on
every call, roughly 15k input tokens each instead of a few hundred, so they
cost around 40x more. Use those to check the plugin inside a real harness, not
for routine runs. Model output varies, so use `--repeat 3` when a result
matters.

## Layout

```
.claude-plugin/plugin.json     Claude Code plugin manifest
hooks/hooks.json               PostToolUse and PreToolUse wiring
scripts/slop_lint.py           the linter, stdlib only, zero model tokens
skills/no-ai-slop/             SKILL.md, eval.md, channels/
skills/no-slop-setup/          installs the style block for any agent
style/no-slop-style.md         the style block itself
commands/                      /deslop and /slop-check
tools/install_style.py         writes the block into CLAUDE.md, AGENTS.md, ...
tools/install_git_hook.py      agent-free commit-msg hook
tools/token_report.py          regenerates the cost table above
evals/                         both suites and their fixtures
```

## Contributing

Pattern reports are the most useful contribution. The linter is only as good as
its catalog, and it is wrong in both directions.

**Found slop it missed?** Add the sentence to
`evals/fixtures/upstream_examples.tsv` with the rule id it should match, or to
`known_misses.tsv` if you think no regex could catch it without false
positives. Then run `python evals/run_evals.py`. A failing test with a real
example is a complete contribution; you do not have to write the regex.

**Got a false positive?** That matters more than a miss. A linter that cries
wolf gets switched off. Add the sentence to a file in `evals/fixtures/clean/`
with `max_findings: 0`, run the suite, and open the issue with the failure
output.

**Adding a pattern:**

1. Add a `Rule(...)` in `scripts/slop_lint.py`. Give it a `reject` regex if the
   pattern has legitimate uses, the way `colon-reveal` exempts clauses with a
   main verb.
2. Add at least one positive example to `upstream_examples.tsv`.
3. Add a near-miss to `fixtures/clean/` that must **not** fire.
4. `python evals/run_evals.py` must stay at zero false positives.

A pattern that raises the false-positive rate above zero will not be merged,
however good the catch rate. Precision over recall, every time.

**Adding a channel:** a rule file in `skills/no-ai-slop/channels/`, a `Channel`
entry in the linter, a row in the SKILL.md router, and an agent case in
`evals/agent_cases.json`. The suite checks that all four exist.

**Editing the style block:** it loads every session for every user, so
additions have to earn their tokens. Re-run `python tools/token_report.py` and
put the new number in the table above.

Run both suites before opening a PR. The agent suite needs a key; say so in the
PR if you could not run it.

## Limits

The regex layer cannot see whether a claim is true, whether a detail is the
useful one, whether cut text carried the writer's voice, or whether the
structure serves the reader. It cannot reliably catch synonym cycling or
abstraction. Those need the model and the skill, which is why
`known_misses.tsv` exists and is tested.

It does not detect whether AI wrote something, and it should not be used to.
Detectors guess and are wrong about people. Named patterns are evidence a human
can check.

## License

MIT. Copyright (c) 2026 Peter Yang and Vivek Siruvuri. See [LICENSE](LICENSE)
and [NOTICE](NOTICE).
