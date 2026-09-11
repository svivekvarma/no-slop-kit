#!/usr/bin/env python3
"""Offline eval and test suite for no-slop-kit.

Four suites, all deterministic and credential-free:

  ground-truth  upstream_examples.tsv, written by the upstream author, so the
                linter is measured against a definition of slop it was not
                tuned on
  known-misses  known_misses.tsv, slop the regex layer cannot catch. Asserted
                to be missed, so the documented limits stay honest
  clean         fixtures/clean, real human prose that must produce no findings
  unit + wiring channel routing, code stripping, bash extraction, ignore globs,
                the two hook contracts, and the style installer

  python evals/run_evals.py
  python evals/run_evals.py --verbose

For the end-to-end test that makes a real model write and then lints what it
wrote, see run_agent_evals.py. That one needs a CLI or an API key; this one
does not, so CI can run it on every push.

Exits non-zero if anything fails.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import slop_lint as sl                      # noqa: E402
import install_style as ist                 # noqa: E402

LINT = os.path.join(ROOT, "scripts", "slop_lint.py")
FIXTURES = os.path.join(ROOT, "evals", "fixtures")


class Results:
    def __init__(self, verbose: bool) -> None:
        self.verbose = verbose
        self.passed = 0
        self.failed: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
            if self.verbose:
                print(f"  pass  {name}")
        else:
            self.failed.append(f"{name}: {detail}")
            print(f"  FAIL  {name}  {detail}")


def read_tsv(path: str) -> list[list[str]]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            rows.append(line.split("\t"))
    return rows


# ---------------------------------------------------------------------------
# Suite 1: independent ground truth
# ---------------------------------------------------------------------------

def suite_ground_truth(r: Results) -> dict:
    print("\nground truth (upstream author's own examples)")
    rows = read_tsv(os.path.join(FIXTURES, "upstream_examples.tsv"))
    by_rule: dict[str, list[bool]] = {}
    for row in rows:
        if len(row) < 3:
            r.check(f"malformed row: {row}", False)
            continue
        rid, channel, text = row[0].strip(), row[1].strip(), row[2]
        found = {f["rid"] for f in sl.lint(text, channel)["findings"]}
        ok = rid in found
        by_rule.setdefault(rid, []).append(ok)
        r.check(f"{rid}: {text[:52]}", ok, f"got {sorted(found) or 'nothing'}")

    hits = sum(sum(v) for v in by_rule.values())
    total = sum(len(v) for v in by_rule.values())
    misses = {k: f"{sum(v)}/{len(v)}" for k, v in sorted(by_rule.items())
              if not all(v)}
    print(f"  recall: {hits}/{total} upstream examples ({hits / total:.0%}) "
          f"across {len(by_rule)} patterns")
    if misses:
        print(f"  incomplete patterns: {misses}")
    return {"hits": hits, "total": total, "patterns": len(by_rule)}


# ---------------------------------------------------------------------------
# Suite 2: documented limits
# ---------------------------------------------------------------------------

def suite_known_misses(r: Results) -> dict:
    print("\nknown misses (what only a model can catch)")
    rows = read_tsv(os.path.join(FIXTURES, "known_misses.tsv"))
    still_missed = 0
    for row in rows:
        if len(row) < 2:
            continue
        category, text = row[0].strip(), row[1]
        findings = sl.lint(text)["findings"]
        ok = not findings
        still_missed += ok
        r.check(f"miss/{category}: {text[:46]}", ok,
                f"now caught by {[f['rid'] for f in findings]} - if that is "
                f"correct, move this line to upstream_examples.tsv")
    print(f"  {still_missed}/{len(rows)} still invisible to the regex layer, "
          "by design")
    return {"missed": still_missed, "total": len(rows)}


# ---------------------------------------------------------------------------
# Suite 3: false positives
# ---------------------------------------------------------------------------

def suite_clean(r: Results) -> dict:
    print("\nclean prose (false positives)")
    directory = os.path.join(FIXTURES, "clean")
    words = 0
    false_positives = 0
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as handle:
            text = handle.read()
        _, meta = sl.prepare(text)
        report = sl.lint(text, meta.get("channel", "default"))
        words += report["words"]
        false_positives += len(report["findings"])

        cap = int(meta.get("max_findings", "0"))
        detail = ", ".join(f"{f['rid']}@L{f['line']}" for f in report["findings"])
        r.check(f"clean/{name} has <= {cap} findings",
                len(report["findings"]) <= cap, detail)
        floor = int(meta.get("min_score", "0"))
        r.check(f"clean/{name} scores >= {floor}", report["score"] >= floor,
                f"scored {report['score']}")

    rate = (false_positives / words * 1000) if words else 0.0
    print(f"  {false_positives} false positives across {words} words "
          f"({rate:.2f} per 1000)")
    return {"words": words, "false_positives": false_positives, "rate": rate}


# ---------------------------------------------------------------------------
# Suite 4: unit and wiring
# ---------------------------------------------------------------------------

def suite_unit(r: Results) -> None:
    print("\nunit")

    for path, want in {
        "docs/runbook.md": "technical-docs",
        "README.md": "technical-docs",
        "blog/2026/shipping.md": "articles-and-blogs",
        ".github/PULL_REQUEST_TEMPLATE.md": "pull-requests",
        "notes/scratch.md": "default",
    }.items():
        r.check(f"detect_channel({path})", sl.detect_channel(path) == want,
                f"got {sl.detect_channel(path)}")

    channels_dir = os.path.join(ROOT, "skills", "no-ai-slop", "channels")
    for name in sl.CHANNELS:
        r.check(f"channels/{name}.md exists",
                os.path.isfile(os.path.join(channels_dir, f"{name}.md")))

    # Code and URLs must be invisible to the linter.
    fenced = "Real text.\n\n```\nHere's the thing. It's not X, it's Y.\n```\n"
    r.check("fenced code is stripped", not sl.lint(fenced)["findings"],
            str(sl.lint(fenced)["findings"]))
    r.check("inline code is stripped",
            not sl.lint("Call `delve_into()` to start.\n")["findings"])
    r.check("urls are stripped",
            not sl.lint("See https://example.com/leverage-robust-delve\n")["findings"])

    # Offsets must survive stripping so line numbers point at the real line.
    text = "Line one.\n\n```\nfenced\n```\n\nHere's the thing. We shipped it.\n"
    findings = sl.lint(text)["findings"]
    r.check("line numbers survive code stripping",
            any(f["line"] == 7 for f in findings),
            str([(f["rid"], f["line"]) for f in findings]))

    _, meta = sl.prepare("---\nslop-lint: off\n---\n\nHere's the thing.\n")
    r.check("front matter opt-out parses", sl.opted_out(meta), str(meta))
    _, meta2 = sl.prepare("---\nchannel: email\n---\n\ntext\n")
    r.check("front matter without opt-out", not sl.opted_out(meta2))

    # A README cannot carry YAML front matter, so the comment form must work.
    _, meta3 = sl.prepare("<!-- slop-lint: off -->\n\n# Title\n\nHere's the thing.\n")
    r.check("html comment opt-out parses", sl.opted_out(meta3), str(meta3))
    _, meta4 = sl.prepare("# Title\n\n<!-- a normal comment -->\n\ntext\n")
    r.check("ordinary html comment is not an opt-out", not sl.opted_out(meta4))

    # The style block carries its own opt-out, so every instruction file it is
    # installed into is exempt. Without this the linter flags its own rules.
    _, meta5 = sl.prepare(ist.style_block(ROOT))
    r.check("style block carries its own opt-out", sl.opted_out(meta5),
            "the block lists the patterns it bans, so it must exempt itself")

    # Nothing in the repo should produce findings: rule files are ignored or
    # opted out, and everything else has to be clean prose.
    patterns_repo = sl.load_ignores(ROOT)
    offenders = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__"}]
        for name in filenames:
            if not name.endswith((".md", ".txt", ".mdc")):
                continue
            path = os.path.join(dirpath, name)
            if sl.is_ignored(path, patterns_repo, ROOT):
                continue
            with open(path, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            _, file_meta = sl.prepare(content)
            if sl.opted_out(file_meta):
                continue
            found = sl.lint(content, sl.detect_channel(path))["findings"]
            if found:
                offenders.append(f"{os.path.relpath(path, ROOT)}: "
                                 f"{[f['rid'] for f in found][:4]}")
    r.check("the repo's own prose passes its own linter", not offenders,
            "; ".join(offenders[:4]))

    patterns = sl.load_ignores(ROOT)
    r.check(".slopignore is read", len(patterns) > len(sl.DEFAULT_IGNORES))
    r.check("channel rule files are ignored",
            sl.is_ignored(os.path.join(ROOT, "skills/no-ai-slop/channels/email.md"),
                          patterns, ROOT))
    r.check("an ordinary doc is not ignored",
            not sl.is_ignored(os.path.join(ROOT, "docs/whatever.md"),
                              patterns, ROOT))

    for command, want in [
        ('git commit -m "Add retry budget to the ingest worker"',
         [("pull-requests", "Add retry budget to the ingest worker")]),
        ('git commit --message="Fix the parser crash on empty rows"',
         [("pull-requests", "Fix the parser crash on empty rows")]),
        ('gh pr create --title "Add retry budget" --body "The worker retried forever."',
         [("pull-requests", "Add retry budget"),
          ("pull-requests", "The worker retried forever.")]),
        ('gh pr comment 4 --body "blocking: this 500s on empty rows"',
         [("review-comments", "blocking: this 500s on empty rows")]),
        ("ls -la", []),
        ('echo "Here is the thing about this"', []),
        ("git commit -m short", []),
    ]:
        got = sl.extract_bash_prose(command)
        r.check(f"extract_bash_prose({command[:42]!r})", got == want, f"got {got}")

    try:
        sl.extract_bash_prose('git commit -m "unclosed')
        r.check("extract_bash_prose survives bad quoting", True)
    except Exception as exc:                                    # noqa: BLE001
        r.check("extract_bash_prose survives bad quoting", False, repr(exc))

    # Channel profiles must change the verdict on identical text.
    headings = "# Title\n\nWe shipped the retry budget on Tuesday.\n"
    r.check("headings flagged in messages",
            any(f["rid"] == "structure-mismatch"
                for f in sl.lint(headings, "messages")["findings"]))
    r.check("headings allowed in technical-docs",
            not any(f["rid"] == "structure-mismatch"
                    for f in sl.lint(headings, "technical-docs")["findings"]))
    r.check("colon-title-case muted in pull-requests",
            not any(f["rid"] == "colon-title-case" for f in
                    sl.lint("Ship it: This is the fix.\n", "pull-requests")["findings"]))

    puffery = "The launch marks a pivotal moment for the company.\n"
    base = sl.lint(puffery, "default")["findings"][0]["severity"]
    amped = sl.lint(puffery, "technical-docs")["findings"][0]["severity"]
    r.check("technical-docs amplifies importance-puffery", amped >= base,
            f"{base} -> {amped}")

    for text in ("", "\n", "hi", "---\n---\n"):
        try:
            r.check(f"lint({text!r}) is safe",
                    isinstance(sl.lint(text)["score"], int))
        except Exception as exc:                                # noqa: BLE001
            r.check(f"lint({text!r}) is safe", False, repr(exc))


# ---------------------------------------------------------------------------
# Suite 5: hook and installer contracts
# ---------------------------------------------------------------------------

def run_hook(event: dict, state: str) -> tuple[int, str]:
    env = dict(os.environ)
    env["NO_SLOP_STATE"] = state
    proc = subprocess.run([sys.executable, LINT, "--hook"], env=env,
                          input=json.dumps(event), capture_output=True,
                          text=True, encoding="utf-8")
    return proc.returncode, (proc.stdout or "").strip()


def suite_wiring(r: Results) -> None:
    print("\nwiring")
    state_dir = tempfile.mkdtemp(prefix="no-slop-eval-")
    write_state = os.path.join(state_dir, "write.json")
    bash_state = os.path.join(state_dir, "bash.json")

    with tempfile.TemporaryDirectory() as tmp:
        sloppy = os.path.join(tmp, "post.md")
        with open(sloppy, "w", encoding="utf-8") as handle:
            handle.write("Here's the thing. It's not a launch, it's a movement.\n"
                         "What nobody tells you is that experts agree.\n")
        event = {"hook_event_name": "PostToolUse", "tool_name": "Write",
                 "cwd": tmp, "tool_input": {"file_path": sloppy}}

        code, out = run_hook(event, write_state)
        payload = json.loads(out) if out.startswith("{") else {}
        hso = payload.get("hookSpecificOutput", {})
        r.check("PostToolUse exits 0", code == 0, f"exit {code}")
        r.check("PostToolUse returns additionalContext",
                bool(hso.get("additionalContext")), out[:160])
        r.check("PostToolUse names its event",
                hso.get("hookEventName") == "PostToolUse")
        r.check("PostToolUse output stays small",
                len(hso.get("additionalContext", "")) < 2000)

        _, out2 = run_hook(event, write_state)
        r.check("PostToolUse is silent on an unchanged repeat", out2 == "",
                out2[:120])

        clean = os.path.join(tmp, "clean.md")
        with open(clean, "w", encoding="utf-8") as handle:
            handle.write("The worker retries three times, then dead-letters the "
                         "batch with its payload.\n")
        _, out3 = run_hook({**event, "tool_input": {"file_path": clean}},
                           write_state)
        r.check("clean file produces no hook output", out3 == "", out3[:120])

        _, out4 = run_hook({**event, "tool_input":
                            {"file_path": os.path.join(tmp, "main.py")}},
                           write_state)
        r.check("non-prose file is skipped", out4 == "", out4[:120])

        _, out5 = run_hook({**event, "tool_input":
                            {"file_path": os.path.join(tmp, "gone.md")}},
                           write_state)
        r.check("missing file is handled", out5 == "", out5[:120])

        proc = subprocess.run([sys.executable, LINT, "--hook"], input="not json",
                              capture_output=True, text=True)
        r.check("malformed hook input exits 0", proc.returncode == 0)

    commit = ('git commit -m "This is not just a refactor, it is a paradigm '
              'shift that underscores our commitment to quality"')
    event = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
             "cwd": ROOT, "tool_input": {"command": commit}}
    code, out = run_hook(event, bash_state)
    hso = (json.loads(out) if out.startswith("{") else {}).get(
        "hookSpecificOutput", {})
    r.check("PreToolUse exits 0", code == 0, f"exit {code}")
    r.check("PreToolUse denies signature slop in a commit message",
            hso.get("permissionDecision") == "deny", out[:200])
    r.check("PreToolUse gives a reason", bool(hso.get("permissionDecisionReason")))
    r.check("PreToolUse names its event", hso.get("hookEventName") == "PreToolUse")

    _, out2 = run_hook(event, bash_state)
    hso2 = (json.loads(out2) if out2.startswith("{") else {}).get(
        "hookSpecificOutput", {})
    r.check("an unchanged retry is not denied again",
            hso2.get("permissionDecision") != "deny", out2[:160])

    _, out3 = run_hook({**event, "tool_input": {"command":
                        'git commit -m "Cap ingest retries at three attempts"'}},
                       bash_state)
    r.check("clean commit message produces no hook output", out3 == "", out3[:150])

    _, out4 = run_hook({**event, "tool_input": {"command": "pytest -q tests/"}},
                       bash_state)
    r.check("unrelated bash command is ignored", out4 == "", out4[:120])

    # CLI contract.
    clean_doc = os.path.join(FIXTURES, "clean", "technical-docs.md")
    proc = subprocess.run([sys.executable, LINT, clean_doc, "--format", "json"],
                          capture_output=True, text=True, encoding="utf-8")
    r.check("CLI --format json exits 0", proc.returncode == 0)
    try:
        data = json.loads(proc.stdout)
        r.check("CLI json has the expected keys",
                {"score", "findings", "channel", "words"} <= set(data))
    except Exception as exc:                                    # noqa: BLE001
        r.check("CLI json has the expected keys", False, repr(exc))

    proc = subprocess.run([sys.executable, LINT, clean_doc, "--min-score", "80"],
                          capture_output=True, text=True, encoding="utf-8")
    r.check("--min-score exits 0 on clean prose", proc.returncode == 0)

    with tempfile.TemporaryDirectory() as tmp:
        bad = os.path.join(tmp, "bad.md")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write("Here's the thing. What nobody tells you is that "
                         "experts agree this marks a pivotal moment.\n")
        proc = subprocess.run([sys.executable, LINT, bad, "--min-score", "80"],
                              capture_output=True, text=True, encoding="utf-8")
        r.check("--min-score exits 1 on slop", proc.returncode == 1,
                f"exit {proc.returncode}")

    # Style installer.
    block = ist.style_block(ROOT)
    r.check("style block has both markers",
            ist.START in block and ist.END in block)
    original = "# My notes\n\nUse tabs.\n"
    once = ist.apply_block(original, block, "")
    twice = ist.apply_block(once, block, "")
    r.check("installer is idempotent", once == twice)
    r.check("installer preserves existing content", "Use tabs." in once)
    r.check("installer inserts exactly one block", once.count(ist.START) == 1)
    removed = ist.remove_block(once)
    r.check("uninstall removes the block", ist.START not in removed)
    r.check("uninstall preserves existing content", "Use tabs." in removed)
    edited = once.replace("Applies to everything", "Applies to EVERYTHING")
    r.check("re-apply restores a modified block",
            "Applies to EVERYTHING" not in ist.apply_block(edited, block, ""))
    for target in ist.TARGETS:
        for rel in (target.user, target.project):
            if rel:
                r.check(f"{target.key} path is relative", not os.path.isabs(rel))

    # Plugin wiring.
    with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"),
              encoding="utf-8") as handle:
        manifest = json.load(handle)
    r.check("plugin.json names the plugin", manifest.get("name") == "no-slop-kit")
    r.check("plugin.json points at hooks",
            manifest.get("hooks") == "./hooks/hooks.json")

    with open(os.path.join(ROOT, "hooks", "hooks.json"), encoding="utf-8") as handle:
        events = json.load(handle).get("hooks", {})
    r.check("hooks.json wires PostToolUse", "PostToolUse" in events)
    r.check("hooks.json wires PreToolUse", "PreToolUse" in events)
    commands = [h["command"] for group in events.values()
                for entry in group for h in entry["hooks"]]
    r.check("hook commands use CLAUDE_PLUGIN_ROOT",
            all("${CLAUDE_PLUGIN_ROOT}" in c for c in commands), str(commands))
    r.check("the linter the hooks call exists", os.path.isfile(LINT))

    for rel in ("skills/no-ai-slop/SKILL.md", "skills/no-slop-setup/SKILL.md"):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
            _, meta = sl.prepare(handle.read())
        r.check(f"{rel} declares a name", bool(meta.get("name")), str(meta)[:100])
        r.check(f"{rel} declares a description", bool(meta.get("description")))

    # Every case in the agent matrix must name a channel the linter knows.
    with open(os.path.join(ROOT, "evals", "agent_cases.json"),
              encoding="utf-8") as handle:
        cases = json.load(handle)
    for case in cases:
        r.check(f"agent case {case['id']} uses a known channel",
                case["channel"] in sl.CHANNELS, case["channel"])


# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_evals.py")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    r = Results(args.verbose)
    truth = suite_ground_truth(r)
    misses = suite_known_misses(r)
    clean = suite_clean(r)
    suite_unit(r)
    suite_wiring(r)

    total = r.passed + len(r.failed)
    print("\n" + "-" * 64)
    print(f"checks        {r.passed}/{total} passed")
    print(f"recall        {truth['hits']}/{truth['total']} upstream examples "
          f"({truth['hits'] / truth['total']:.0%}) over {truth['patterns']} patterns")
    print(f"known misses  {misses['missed']}/{misses['total']} left to the model")
    print(f"false pos.    {clean['false_positives']} in {clean['words']} words "
          f"({clean['rate']:.2f} per 1000)")
    if r.failed:
        print(f"\n{len(r.failed)} failed:")
        for line in r.failed:
            print(f"  - {line}")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
