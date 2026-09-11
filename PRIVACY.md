<!-- slop-lint: off -->

# Privacy

No Slop Kit has no server, no account and no telemetry of its own.

The kit has three layers, and only one of them involves a model.

**The linter** (`scripts/slop_lint.py`) is the detection layer: Python standard
library, regular expressions, no model. It reads the files you point it at and
prints what it found. It makes no network calls and needs no API key, which is
why it can run in a git hook and in CI. This is the layer this page can make
absolute promises about.

**The style block** is text in your agent's instruction file. It is never sent
anywhere by this project; your agent loads it the same way it loads the rest of
that file.

**The skill** is the judgement layer, and it is your agent doing the editing.
Regex cannot tell whether a claim is true, whether a cut sentence carried your
voice, or whether a paragraph is empty but grammatical, so that work belongs to
the model. See the section below for what that means for your text.

When you use the skill or the hooks inside a coding agent, your text is
processed by that agent (Claude Code, Codex, Cursor, Gemini CLI, Copilot,
Windsurf) under that product's own privacy terms. This project adds nothing to
what your agent already sends.

`evals/run_agent_evals.py` is the one part that calls a model, and only when
you run it yourself. It sends the prompts in `evals/agent_cases.json`, which
contain no personal data, to the Anthropic API or to a CLI you have installed.
It is not run by the plugin, the hooks or the skill.

The hook keeps one small file in your system temp directory recording a hash
of each file it has already reported on, so it does not report the same version
twice. It holds hashes and paths, no content. Delete it at any time, or point
it elsewhere with `NO_SLOP_STATE`.

Questions: open an issue at
https://github.com/svivekvarma/no-slop-kit/issues
