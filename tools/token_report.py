#!/usr/bin/env python3
"""Measure what no-slop-kit costs in context tokens.

Every file a plugin loads competes with the user's actual work for context, so
the cost belongs in the README as a number rather than a reassurance.

  python tools/token_report.py
  python tools/token_report.py --exact      # count_tokens API, needs a key
  python tools/token_report.py --markdown   # table for the README

Without --exact this estimates at 3.7 characters per token, which is close for
English prose. With a key it calls the Anthropic count_tokens endpoint, which
costs nothing and returns the real count for the tokenizer in use.
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARS_PER_TOKEN = 3.7

START = "<!-- no-slop-kit:start -->"
END = "<!-- no-slop-kit:end -->"

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
        return handle.read()


def style_block() -> str:
    text = read("style/no-slop-style.md")
    return text[text.find(START):text.find(END) + len(END)]


def counter(exact: bool):
    if not exact:
        return lambda text: round(len(text) / CHARS_PER_TOKEN), "estimated"
    try:
        import anthropic
    except ImportError:
        print("anthropic SDK not installed; falling back to estimates",
              file=sys.stderr)
        return lambda text: round(len(text) / CHARS_PER_TOKEN), "estimated"
    client = anthropic.Anthropic()
    model = os.environ.get("NO_SLOP_COUNT_MODEL", "claude-haiku-4-5")

    def count(text: str) -> int:
        result = client.messages.count_tokens(
            model=model, messages=[{"role": "user", "content": text or " "}])
        return result.input_tokens

    return count, f"exact ({model})"


# what it is, path, when it loads
ROWS = [
    ("style block", None, "every session, once installed"),
    ("no-slop SKILL.md", "skills/no-ai-slop/SKILL.md", "only when the skill runs"),
    ("eval.md", "skills/no-ai-slop/eval.md", "only when the skill self-checks"),
    ("one channel file", None, "only when the skill runs, one of nine"),
    ("no-slop-setup SKILL.md", "skills/no-slop-setup/SKILL.md",
     "only when installing"),
    ("/deslop command", "commands/deslop.md", "only when invoked"),
    ("/slop-check command", "commands/slop-check.md", "only when invoked"),
]

CHANNELS = [
    "technical-docs", "articles-and-blogs", "email", "messages",
    "social-posts", "social-comments", "code-comments", "pull-requests",
    "review-comments", "default",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="token_report.py")
    parser.add_argument("--exact", action="store_true",
                        help="use the count_tokens API instead of estimating")
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args(argv)

    count, method = counter(args.exact)

    channel_counts = {
        name: count(read(f"skills/no-ai-slop/channels/{name}.md"))
        for name in CHANNELS
    }
    largest = max(channel_counts, key=channel_counts.get)

    rows = []
    for label, path, when in ROWS:
        if label == "style block":
            tokens = count(style_block())
        elif label == "one channel file":
            tokens = channel_counts[largest]
            when += f" (largest: {largest})"
        else:
            tokens = count(read(path))
        rows.append((label, tokens, when))

    # The hook's own output, which is the only thing the linter ever adds.
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import slop_lint as sl
    sample = ("Here's the thing. It's not a launch, it's a movement. What "
              "nobody tells you is that experts agree this marks a pivotal "
              "moment, highlighting our commitment to innovation.\n")
    report = sl.lint(sample, "articles-and-blogs")
    actionable = [f for f in report["findings"] if f["severity"] >= 2]
    hook_text = "\n".join(
        [f"slop-lint: draft.md scores {report['score']}/100 "
         f"({report['grade']}) on the {report['channel']} profile.",
         "Findings below are from a regex linter, not a judgement about the "
         "writing. Fix the ones that are real slop in context and ignore the "
         "rest. Do not re-run the linter; it re-checks on the next write."]
        + [f"- L{f['line']} {f['rid']}: \"{f['quote']}\" -> {f['fix']}"
           for f in actionable[:8]])
    hook_tokens = count(hook_text)

    always = rows[0][1]
    on_demand = sum(t for label, t, _ in rows if label != "style block")

    if args.markdown:
        print(f"| What | Tokens | When it loads |")
        print(f"| --- | ---: | --- |")
        for label, tokens, when in rows:
            print(f"| {label} | {tokens:,} | {when} |")
        print(f"| hook finding report | ~{hook_tokens:,} | "
              f"only on a write that has slop in it |")
        print()
        print(f"Always-on cost: **{always:,} tokens per session**. "
              f"Everything else loads only when used. Counts are {method}.")
        return 0

    print(f"no-slop-kit context cost   ({method}, "
          f"{CHARS_PER_TOKEN} chars/token when estimated)\n")
    print(f"{'what':26} {'tokens':>7}  when it loads")
    print("-" * 78)
    for label, tokens, when in rows:
        print(f"{label:26} {tokens:>7,}  {when}")
    print(f"{'hook finding report':26} {hook_tokens:>7,}  "
          f"only on a write that has slop in it")
    print("-" * 78)
    print(f"{'always on':26} {always:>7,}  the style block, every session")
    print(f"{'on demand, worst case':26} {on_demand:>7,}  "
          f"if every skill and command ran in one session")
    print()
    print("all channel files:")
    for name, tokens in sorted(channel_counts.items(),
                               key=lambda kv: -kv[1]):
        print(f"  {name:22} {tokens:>6,}")
    print("\nThe linter itself costs zero model tokens: it is regex in a "
          "subprocess.\nOnly its findings enter context, and only for a file "
          "that has slop in it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
