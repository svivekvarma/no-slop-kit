<!-- slop-lint: off -->

# Changes from petergyang/no-ai-slop

Upstream: https://github.com/petergyang/no-ai-slop (MIT, Copyright (c) 2026
Peter Yang), at commit `000650b156983f5159695b441477f4e63b25dc85`.

See [NOTICE](NOTICE) for the file-by-file provenance. This file explains the
reasoning behind each change.

## Kept as it is

The slop catalog is upstream's and it is the part worth keeping. The editing
principles, the words-to-cut lists, the pattern definitions and the eval
questions are reproduced in `skills/no-ai-slop/SKILL.md` and `eval.md` with
light edits, under provenance headers. The two jobs, edit and detect, work the
same way. The refusal to guess whether AI wrote a piece is kept deliberately:
detectors are wrong about people, and named patterns are checkable.

## Added

**A deterministic linter** (`scripts/slop_lint.py`). Upstream's patterns
encoded as regex, so the mechanical two thirds of slop can be caught with no
model, no key and no network. This is what makes the hooks, the git hook and
the CI job possible. It is measured against upstream's own example sentences in
`evals/fixtures/upstream_examples.tsv`.

**Channels** (`skills/no-ai-slop/channels/`). Upstream treats prose as prose.
That flattens a real distinction: a Slack message with headings is slop, a
runbook without them is worse; a PR body that summarises the diff is useless
because the reviewer has the diff; a code comment that narrates the line below
it is noise. Nine channel files hold only what differs from the shared rules,
and the linter changes which rules apply and how hard. The skill reads exactly
one of them, so the context cost is one file, not nine.

**Hooks** (`hooks/hooks.json`). Upstream is invoked. Most slop is never pasted
into a chat window: it goes into a commit message or a runbook and gets merged.
A `PostToolUse` hook lints every prose file the agent writes and hands back the
findings. A `PreToolUse` hook reads the message text out of `git commit`,
`gh pr create`, `gh issue create` and `gh pr comment` before it is published,
and blocks once on signature slop so the text can be reworded. Re-running the
same command is allowed, so it cannot wedge anyone.

**A style block** (`style/no-slop-style.md`). 664 tokens in the agent's
instruction file, so slop is not generated in the first place. Cheaper than
editing it out afterwards.

**Cross-tool support** (`tools/install_style.py`). Upstream ships a ChatGPT and
Codex plugin manifest. This installs the same rules into `CLAUDE.md`,
`AGENTS.md`, `GEMINI.md`, Cursor rules, Copilot instructions or Windsurf rules,
at user or project scope, idempotently. Plus a git `commit-msg` hook and a
GitHub Action for people who use no AI tool at all.

**Tests** (`evals/`). Upstream's `eval.md` is a rubric the model applies to
itself. This adds a suite that runs: 182 deterministic checks including recall
against upstream's examples, a zero-false-positive guard, and an asserted
known-miss corpus that keeps the documented limits honest. Plus an end-to-end
suite that has a real model write in each channel, with and without the style
block, and lints both.

## Deliberately not copied

**`.codex-plugin/plugin.json`.** Upstream's ChatGPT and Codex plugin manifest
names Peter Yang as author and points at his website, newsletter and brand
color. Shipping it would misattribute this project to him; editing the author
field to point here would strip his attribution. Neither is acceptable, so it
is omitted. Codex users get `AGENTS.md` instead, via `install_style.py`.

**`assets/no-ai-slop.png`** and the brand color, for the same reason.

**`agents/openai.yaml`.** Upstream's ChatGPT interface metadata, tied to that
plugin listing.

**`PRIVACY.md` and `TERMS.md`.** Both end in Peter Yang's email address.
Forwarding them would send this project's support mail to him. `PRIVACY.md` is
rewritten from scratch here; the terms are covered by the MIT license.

## Changed

**Skill name.** Upstream's skill is `no-ai-slop`; this one is `no-slop`, so
both can be installed side by side without a name collision. The directory
keeps the upstream name to make the provenance obvious.

**`eval.md`** gains a channel section and a linter cross-check, including a
question that asks whether any edit was made only to satisfy the linter. The
upstream questions are unchanged.

**Words to cut** gains a few entries the linter needed: seamless, unlock,
unleash, plethora, myriad, holistic, synergy, and the email and chat openers
("I hope this email finds you well", "just circling back", "great question")
that the email and messages channels treat as throat-clearing.
