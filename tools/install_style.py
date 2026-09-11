#!/usr/bin/env python3
"""Install the no-slop style block into an agent's instruction file.

Works with Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot and Windsurf,
at user scope or project scope. Idempotent: the block is delimited by HTML
comment markers, so re-running replaces the block in place instead of appending
a second copy.

  python tools/install_style.py --list
  python tools/install_style.py --target claude --scope user
  python tools/install_style.py --target all --scope project
  python tools/install_style.py --target codex --scope user --dry-run
  python tools/install_style.py --target claude --scope user --uninstall

Standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass

START = "<!-- no-slop-kit:start -->"
END = "<!-- no-slop-kit:end -->"

# Cursor wants its own front matter, so it gets a wrapper.
CURSOR_FRONTMATTER = """---
description: No-slop writing style
alwaysApply: true
---

"""


@dataclass
class Target:
    key: str
    label: str
    user: str | None        # path relative to the home directory
    project: str | None     # path relative to the project root
    wrapper: str = ""

    def path_for(self, scope: str, root: str) -> str | None:
        rel = self.user if scope == "user" else self.project
        if rel is None:
            return None
        base = os.path.expanduser("~") if scope == "user" else root
        return os.path.join(base, *rel.split("/"))


TARGETS: list[Target] = [
    Target("claude", "Claude Code",
           ".claude/CLAUDE.md", "CLAUDE.md"),
    Target("codex", "Codex CLI / any AGENTS.md-aware agent",
           ".codex/AGENTS.md", "AGENTS.md"),
    Target("gemini", "Gemini CLI",
           ".gemini/GEMINI.md", "GEMINI.md"),
    Target("cursor", "Cursor",
           None, ".cursor/rules/no-slop.mdc", CURSOR_FRONTMATTER),
    Target("copilot", "GitHub Copilot",
           None, ".github/copilot-instructions.md"),
    Target("windsurf", "Windsurf",
           None, ".windsurf/rules/no-slop.md"),
]

BY_KEY = {t.key: t for t in TARGETS}


def style_block(repo_root: str) -> str:
    """Read the style file and return just the marked block."""
    path = os.path.join(repo_root, "style", "no-slop-style.md")
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    start = text.find(START)
    end = text.find(END)
    if start == -1 or end == -1:
        raise SystemExit(f"markers not found in {path}")
    return text[start:end + len(END)].strip() + "\n"


def apply_block(existing: str, block: str, wrapper: str) -> str:
    """Insert or replace the marked block, leaving everything else alone."""
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END),
                         re.DOTALL)
    if pattern.search(existing):
        return pattern.sub(block.strip(), existing)
    prefix = existing
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix.strip():
        prefix += "\n"
    elif wrapper:
        prefix = wrapper
    return prefix + block


def remove_block(existing: str) -> str:
    pattern = re.compile(r"\n*" + re.escape(START) + r".*?" + re.escape(END) + r"\n*",
                         re.DOTALL)
    return pattern.sub("\n", existing).strip() + "\n"


def install(target: Target, scope: str, root: str, block: str,
            dry_run: bool, uninstall: bool) -> str:
    path = target.path_for(scope, root)
    if path is None:
        return f"skip   {target.key:9} no {scope}-scope location for this tool"

    existing = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            existing = handle.read()

    if uninstall:
        if START not in existing:
            return f"skip   {target.key:9} nothing installed at {path}"
        updated = remove_block(existing)
        verb = "remove"
    else:
        updated = apply_block(existing, block, target.wrapper)
        verb = "update" if START in existing else "install"

    if updated == existing:
        return f"ok     {target.key:9} already current at {path}"
    if dry_run:
        return f"would {verb} {target.key:9} {path}"

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)
    return f"{verb:6} {target.key:9} {path}"


def main(argv: list[str] | None = None) -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(
        prog="install_style.py",
        description="Install the no-slop style block into an agent config file.")
    parser.add_argument("--target", default="claude",
                        help="one of: " + ", ".join(BY_KEY) + ", all")
    parser.add_argument("--scope", default="user", choices=("user", "project"),
                        help="user scope applies everywhere; project scope is "
                             "committed with the repo")
    parser.add_argument("--project-root", default=os.getcwd(),
                        help="project root for --scope project")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--list", action="store_true",
                        help="show supported targets and their paths")
    args = parser.parse_args(argv)

    if args.list:
        print(f"{'target':10} {'tool':45} {'user scope':28} project scope")
        for t in TARGETS:
            print(f"{t.key:10} {t.label:45} "
                  f"{'~/' + t.user if t.user else '-':28} "
                  f"{t.project or '-'}")
        return 0

    if args.target == "all":
        chosen = TARGETS
    elif args.target in BY_KEY:
        chosen = [BY_KEY[args.target]]
    else:
        parser.error(f"unknown target: {args.target}")
        return 2

    block = style_block(repo_root)
    for target in chosen:
        print(install(target, args.scope, os.path.abspath(args.project_root),
                      block, args.dry_run, args.uninstall))
    return 0


if __name__ == "__main__":
    sys.exit(main())
