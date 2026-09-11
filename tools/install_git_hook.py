#!/usr/bin/env python3
"""Install a git commit-msg hook that lints the commit message for slop.

Agent-free: this works for teammates who use no AI tool at all.

  python tools/install_git_hook.py
  python tools/install_git_hook.py --repo /path/to/repo
  python tools/install_git_hook.py --uninstall

The hook warns and always exits 0, so it can never block a commit. Set
NO_SLOP_STRICT=1 in the environment to make it reject a message that contains
signature slop instead.
"""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys

MARKER = "# no-slop-kit commit-msg hook"

HOOK = """#!/bin/sh
{marker}
# Lints the commit message with scripts/slop_lint.py. Warns by default.
# NO_SLOP_STRICT=1 makes it reject signature slop.

MSG_FILE="$1"
LINT="{lint}"

[ -f "$LINT" ] || exit 0
command -v python >/dev/null 2>&1 && PY=python || PY=python3
command -v "$PY" >/dev/null 2>&1 || exit 0

# Strip comment lines git adds to the template before linting.
TMP="$(mktemp)"
grep -v '^#' "$MSG_FILE" > "$TMP"

OUT="$("$PY" "$LINT" "$TMP" --channel pull-requests --min-score 60 2>&1)"
STATUS=$?
rm -f "$TMP"

if [ $STATUS -ne 0 ]; then
  echo ""
  echo "no-slop-kit: this commit message reads as AI slop."
  echo "$OUT"
  echo ""
  if [ "$NO_SLOP_STRICT" = "1" ]; then
    echo "Rejected because NO_SLOP_STRICT=1. Reword and commit again."
    exit 1
  fi
  echo "Committing anyway. Set NO_SLOP_STRICT=1 to reject instead."
fi

exit 0
"""


def git_dir(repo: str) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--absolute-git-dir"],
            cwd=repo, capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise SystemExit(f"not a git repository: {repo}")


def main(argv: list[str] | None = None) -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(prog="install_git_hook.py")
    parser.add_argument("--repo", default=os.getcwd(),
                        help="repository to install the hook into")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args(argv)

    hooks_dir = os.path.join(git_dir(os.path.abspath(args.repo)), "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    path = os.path.join(hooks_dir, "commit-msg")

    if args.uninstall:
        if not os.path.isfile(path):
            print("skip    no commit-msg hook installed")
            return 0
        with open(path, encoding="utf-8", errors="replace") as handle:
            if MARKER not in handle.read():
                print(f"skip    {path} was not installed by no-slop-kit; "
                      "leaving it alone")
                return 0
        os.remove(path)
        print(f"removed {path}")
        return 0

    if os.path.isfile(path):
        with open(path, encoding="utf-8", errors="replace") as handle:
            existing = handle.read()
        if MARKER not in existing:
            print(f"refuse  {path} already exists and was not written by "
                  "no-slop-kit.\n        Move it aside or add the lint call to "
                  "it by hand.")
            return 1

    lint = os.path.join(repo_root, "scripts", "slop_lint.py").replace("\\", "/")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(HOOK.format(marker=MARKER, lint=lint))
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP)
    print(f"install {path}")
    print("        warns on slop; set NO_SLOP_STRICT=1 to reject instead")
    return 0


if __name__ == "__main__":
    sys.exit(main())
