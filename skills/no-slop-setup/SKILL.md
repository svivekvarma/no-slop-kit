---
name: no-slop-setup
description: Install, update or remove the no-slop writing style block in an agent instruction file (CLAUDE.md, AGENTS.md, GEMINI.md, Cursor rules, Copilot instructions or Windsurf rules), at user scope or project scope. Also wires the optional git pre-commit hook. Use when the user asks to set up no-slop, add the writing style to CLAUDE.md, apply the style globally or to one project, install it for Codex or Cursor or Gemini, or uninstall it.
slop-lint: off
---

# No-slop setup

Install the no-slop writing style block into the instruction file that the
user's agent actually reads. The block makes the agent write without slop in
ordinary conversation, so the user does not have to invoke a skill every time.

## Two decisions

Ask only what you cannot infer.

**Which tool.** `claude`, `codex`, `gemini`, `cursor`, `copilot`, `windsurf`, or
`all`. If the user is running Claude Code and says nothing else, use `claude`.
If they mention Codex, Cursor, Gemini or Copilot, use that one. `codex` writes
`AGENTS.md`, which several other agents also read.

**Which scope.**

- `user` applies to every project on the machine. Use this when the user says globally, everywhere, at user level, or all my projects. Claude, Codex and Gemini support this. Cursor, Copilot and Windsurf have no user-scope file, so they are skipped with a message.
- `project` writes a file in the repo that gets committed, so a team shares it. Use this when the user says this repo, this project, or for the team.

Default to `--scope user` with `--target claude` when the user just says "set up
no-slop" inside Claude Code.

## Run it

```sh
python tools/install_style.py --list
python tools/install_style.py --target claude --scope user
python tools/install_style.py --target all --scope project
python tools/install_style.py --target codex --scope user --dry-run
python tools/install_style.py --target claude --scope user --uninstall
```

Run `--dry-run` first and show the user which paths will change when the target
is `all`, or whenever the scope is `user`, because that edits a file outside the
project. Then run it for real.

The block is delimited by `<!-- no-slop-kit:start -->` and
`<!-- no-slop-kit:end -->`. Running the installer again replaces the block in
place and leaves the rest of the file untouched, so it is safe on a file the
user has already written by hand. Never hand-edit those files to install the
block; use the script so the markers stay correct.

## Optional: the git pre-commit hook

This catches slop in commit messages with no agent involved, which is useful for
the user's teammates who do not run an AI tool at all.

```sh
python tools/install_git_hook.py            # install into .git/hooks/commit-msg
python tools/install_git_hook.py --uninstall
```

Mention it only if the user asks about commits, CI, teammates, or enforcement.
It warns and does not block, so it cannot wedge anyone's commit.

## After installing

Tell the user three things, briefly:

1. Which file changed, by full path.
2. That they need to restart their agent session for a user-scope change to load.
3. The context cost, which is about 560 tokens per session for the block. Point at the token table in `README.md` if they want the full accounting.

Do not paste the style block into the chat. Do not summarise its rules back to
the user unless they ask what it contains.
