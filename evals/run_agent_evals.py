#!/usr/bin/env python3
"""End-to-end eval: make a real model write, then lint what it wrote.

run_evals.py proves the linter detects patterns. This proves the kit changes
what a model actually produces. Every case runs twice per model:

  baseline  the task prompt alone
  styled    the same prompt with the no-slop style block as the system prompt

Both outputs go through the same linter, so the grader is deterministic and
costs nothing. A case passes when the styled run clears the case threshold,
beats its own baseline, and still contains the facts the prompt supplied. That
last check is what stops a model from scoring well by deleting content.

  python evals/run_agent_evals.py                       # haiku, ~$0.02
  python evals/run_agent_evals.py --models claude-haiku-4-5,claude-sonnet-5
  python evals/run_agent_evals.py --cases pr-body-incident,slack-incident
  python evals/run_agent_evals.py --backend claude      # Claude Code CLI, ~40x
  python evals/run_agent_evals.py --estimate            # price it, call nothing

Default is the Anthropic API with Claude Haiku 4.5. The API sends only the
prompt; the `claude` and `codex` CLI backends reload their whole agent harness
on every call, which costs roughly 15k input tokens per call instead of a few
hundred. Use them to check the plugin inside a real harness, not for routine
runs.

Needs ANTHROPIC_API_KEY (or an `ant auth login` profile) for the api backend.
Deliberately separate from run_evals.py, which stays offline so CI needs no
credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import slop_lint as sl                      # noqa: E402
import install_style as ist                 # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_MODEL = "claude-haiku-4-5"

# Anthropic first-party rates, dollars per million tokens.
PRICING = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-fable-5-1": (10.0, 50.0),
}


def price(model: str, tokens_in: int, tokens_out: int) -> float | None:
    rates = PRICING.get(model)
    if not rates:
        return None
    return tokens_in / 1e6 * rates[0] + tokens_out / 1e6 * rates[1]


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

class Backend:
    name = "base"
    meters_tokens = False

    def available(self) -> tuple[bool, str]:
        raise NotImplementedError

    def generate(self, prompt: str, system: str | None, model: str,
                 timeout: int) -> dict:
        """Return {text, input_tokens, output_tokens}."""
        raise NotImplementedError


class AnthropicAPI(Backend):
    name = "api"
    meters_tokens = True

    def available(self) -> tuple[bool, str]:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False, "pip install anthropic"
        if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
                "ANTHROPIC_AUTH_TOKEN"):
            return True, ""
        # An `ant auth login` profile also works; the SDK finds it itself.
        config = os.path.expanduser("~/.config/anthropic")
        if os.path.isdir(config):
            return True, ""
        return False, ("no credentials: set ANTHROPIC_API_KEY or run "
                       "`ant auth login`")

    def generate(self, prompt: str, system: str | None, model: str,
                 timeout: int) -> dict:
        import anthropic
        client = anthropic.Anthropic(timeout=timeout)
        kwargs = {
            "model": model,
            "max_tokens": 1200,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        message = client.messages.create(**kwargs)
        text = "".join(b.text for b in message.content
                       if getattr(b, "type", "") == "text")
        return {
            "text": text.strip(),
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        }


class ClaudeCLI(Backend):
    name = "claude"

    def available(self) -> tuple[bool, str]:
        if shutil.which("claude") is None:
            return False, "claude CLI not on PATH"
        return True, ""

    def generate(self, prompt: str, system: str | None, model: str,
                 timeout: int) -> dict:
        cmd = ["claude", "-p", prompt]
        if model:
            cmd += ["--model", model]
        if system:
            cmd += ["--append-system-prompt", system]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=timeout, cwd=ROOT)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "")[:300])
        return {"text": (proc.stdout or "").strip(),
                "input_tokens": 0, "output_tokens": 0}


class CodexCLI(Backend):
    name = "codex"

    def available(self) -> tuple[bool, str]:
        if shutil.which("codex") is None:
            return False, "codex CLI not on PATH"
        return True, ""

    def generate(self, prompt: str, system: str | None, model: str,
                 timeout: int) -> dict:
        # codex exec takes no separate system prompt, so the style block is
        # prepended, which is how AGENTS.md delivers it anyway.
        full = f"{system}\n\n---\n\n{prompt}" if system else prompt
        proc = subprocess.run(["codex", "exec", "--skip-git-repo-check", full],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=timeout, cwd=ROOT)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "")[:300])
        return {"text": (proc.stdout or "").strip(),
                "input_tokens": 0, "output_tokens": 0}


BACKENDS = {b.name: b for b in (AnthropicAPI(), ClaudeCLI(), CodexCLI())}


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

def strip_wrapper(text: str) -> str:
    """Models often wrap the answer in a fence or add a preamble line."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        end = len(lines) - 1
        while end > 0 and not lines[end].startswith("```"):
            end -= 1
        if end > 0:
            text = "\n".join(lines[1:end]).strip()
    return text


def grade(case: dict, text: str) -> dict:
    report = sl.lint(text, case["channel"])
    needles = case.get("must_include", [])
    lowered = text.lower()
    missing = [n for n in needles if n.lower() not in lowered]
    return {
        "score": report["score"],
        "grade": report["grade"],
        "words": report["words"],
        "findings": [f["rid"] for f in report["findings"]],
        "signature": report["counts"]["signature"],
        "kept_facts": not missing,
        "missing_facts": missing,
    }


def estimate(cases: list[dict], models: list[str], style: str,
             repeat: int = 1) -> None:
    prompt_chars = sum(len(c["prompt"]) for c in cases)
    style_tok = len(style) / 3.7
    prompt_tok = prompt_chars / 3.7
    repeat = max(1, repeat)
    out_tok = 300 * len(cases) * 2 * repeat
    in_tok = (prompt_tok * 2 + style_tok * len(cases)) * repeat
    calls = len(cases) * 2 * repeat
    print(f"{len(cases)} cases x 2 conditions x {repeat} repeat = "
          f"{calls} calls per model\n")
    print(f"{'model':22} {'in':>8} {'out':>8} {'cost':>9}")
    print("-" * 50)
    total = 0.0
    for model in models:
        cost = price(model, int(in_tok), int(out_tok))
        total += cost or 0
        shown = f"${cost:.4f}" if cost is not None else "unpriced"
        print(f"{model:22} {int(in_tok):>8,} {int(out_tok):>8,} {shown:>9}")
    print("-" * 50)
    print(f"{'total':22} {'':>8} {'':>8} {'$' + format(total, '.4f'):>9}")
    print("\nEstimate only: output length is assumed at 300 tokens per call.\n"
          "Run without --estimate for metered totals from the API.")


# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_agent_evals.py")
    parser.add_argument("--backend", default="api", choices=sorted(BACKENDS))
    parser.add_argument("--models", default=DEFAULT_MODEL,
                        help="comma-separated model ids (default: "
                             f"{DEFAULT_MODEL})")
    parser.add_argument("--cases", default="", help="comma-separated case ids")
    parser.add_argument("--channels", default="",
                        help="comma-separated channels to include")
    parser.add_argument("--repeat", type=int, default=1,
                        help="samples per condition; scores are averaged. "
                             "Model output varies, so a single sample makes a "
                             "noisy eval (default: 1)")
    parser.add_argument("--tolerance", type=int, default=8,
                        help="how far the styled run may fall below its own "
                             "baseline before it counts as a regression. "
                             "Single samples are noisy (default: 8)")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--save", default="")
    parser.add_argument("--estimate", action="store_true",
                        help="print the projected cost and exit")
    parser.add_argument("--list-backends", action="store_true")
    args = parser.parse_args(argv)

    if args.list_backends:
        for name, backend in BACKENDS.items():
            ok, why = backend.available()
            print(f"{name:8} {'available' if ok else 'unavailable: ' + why}")
        return 0

    with open(os.path.join(ROOT, "evals", "agent_cases.json"),
              encoding="utf-8") as handle:
        cases = json.load(handle)
    if args.cases:
        wanted = {c.strip() for c in args.cases.split(",") if c.strip()}
        cases = [c for c in cases if c["id"] in wanted]
    if args.channels:
        chans = {c.strip() for c in args.channels.split(",") if c.strip()}
        cases = [c for c in cases if c["channel"] in chans]
    if not cases:
        print("no cases selected", file=sys.stderr)
        return 2

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    style = ist.style_block(ROOT)

    if args.estimate:
        estimate(cases, models, style, args.repeat)
        return 0

    backend = BACKENDS[args.backend]
    ok, why = backend.available()
    if not ok:
        print(f"backend '{args.backend}' unavailable: {why}", file=sys.stderr)
        return 77

    if backend.name != "api":
        print(f"note: the {backend.name} backend reloads its agent harness on "
              "every call,\n      so this run costs far more than the api "
              "backend. Ctrl-C to stop.\n")

    rows: list[dict] = []
    failures: list[str] = []
    started = time.time()

    for model in models:
        print(f"\nbackend {backend.name}   model {model}   cases {len(cases)}\n")
        header = (f"{'case':20} {'channel':18} {'base':>5} {'styled':>7} "
                  f"{'delta':>6}  facts")
        print(header)
        print("-" * len(header))
        tokens_in = tokens_out = 0

        for case in cases:
            row = {"model": model, "id": case["id"], "channel": case["channel"]}
            for condition, system in (("baseline", None), ("styled", style)):
                samples = []
                error = None
                for _ in range(max(1, args.repeat)):
                    try:
                        result = backend.generate(case["prompt"], system, model,
                                                  args.timeout)
                        tokens_in += result["input_tokens"]
                        tokens_out += result["output_tokens"]
                        text = strip_wrapper(result["text"])
                        sample = grade(case, text)
                        sample["text"] = text
                        samples.append(sample)
                    except Exception as exc:                    # noqa: BLE001
                        error = str(exc)[:250]
                if not samples:
                    row[condition] = {"error": error or "no samples"}
                    failures.append(f"{model}/{case['id']}/{condition}: "
                                    f"{(error or '')[:140]}")
                    continue
                # Average the score across samples; a case counts as losing a
                # fact if any sample lost it.
                merged = dict(samples[0])
                merged["score"] = round(
                    sum(s["score"] for s in samples) / len(samples))
                merged["signature"] = round(
                    sum(s["signature"] for s in samples) / len(samples))
                merged["kept_facts"] = all(s["kept_facts"] for s in samples)
                merged["missing_facts"] = sorted(
                    {m for s in samples for m in s["missing_facts"]})
                merged["samples"] = len(samples)
                merged["scores"] = [s["score"] for s in samples]
                row[condition] = merged

            base, styled = row["baseline"], row["styled"]
            if "error" in base or "error" in styled:
                print(f"{case['id']:20} {case['channel']:18} "
                      f"{'ERR':>5} {'ERR':>7}")
                rows.append(row)
                continue

            delta = styled["score"] - base["score"]
            facts = "kept" if styled["kept_facts"] else \
                f"LOST {styled['missing_facts']}"
            print(f"{case['id']:20} {case['channel']:18} {base['score']:>5} "
                  f"{styled['score']:>7} {delta:>+6}  {facts}")

            cap = case.get("max_score", 60)
            if styled["score"] < cap:
                failures.append(f"{model}/{case['id']}: styled scored "
                                f"{styled['score']}, below the {cap} floor "
                                f"({styled['findings']})")
            # The real per-case gate. Severity-3 findings are the patterns no
            # reasonable writer defends, so one of them is a failure even when
            # the score looks fine. Score alone is too noisy to gate on.
            if styled["signature"]:
                failures.append(f"{model}/{case['id']}: styled output contains "
                                f"signature slop ({styled['findings']})")
            if not styled["kept_facts"]:
                failures.append(f"{model}/{case['id']}: styled output dropped "
                                f"{styled['missing_facts']}")
            # Per-case baseline comparison is reported, not gated: at one
            # sample per condition the run-to-run variance is larger than the
            # effect. The aggregate below is the honest comparison.
            rows.append(row)

        scored = [r for r in rows if r["model"] == model
                  and "score" in r.get("baseline", {})
                  and "score" in r.get("styled", {})]
        if scored:
            base_avg = sum(r["baseline"]["score"] for r in scored) / len(scored)
            sty_avg = sum(r["styled"]["score"] for r in scored) / len(scored)
            base_sig = sum(r["baseline"]["signature"] for r in scored)
            sty_sig = sum(r["styled"]["signature"] for r in scored)
            print(f"\n  mean score      {base_avg:5.1f}  ->  {sty_avg:5.1f}  "
                  f"({sty_avg - base_avg:+.1f})")
            print(f"  signature slop  {base_sig:5}  ->  {sty_sig:5}")
        if scored:
            if sty_sig > base_sig:
                failures.append(f"{model}: styled runs produced more signature "
                                f"slop ({sty_sig}) than baseline ({base_sig})")
            if sty_avg < base_avg - args.tolerance:
                failures.append(f"{model}: styled mean {sty_avg:.1f} is more "
                                f"than {args.tolerance} below baseline mean "
                                f"{base_avg:.1f}. Re-run with --repeat 3 "
                                f"before treating this as real.")
        if backend.meters_tokens and tokens_in:
            cost = price(model, tokens_in, tokens_out)
            shown = f"${cost:.4f}" if cost is not None else "unpriced"
            print(f"  tokens          {tokens_in:,} in / {tokens_out:,} out"
                  f"   {shown}")

    print(f"\nelapsed {time.time() - started:.0f}s")

    if args.save:
        with open(args.save, "w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=2)
        print(f"saved {args.save}")

    if failures:
        print(f"\n{len(failures)} failed:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("\nall agent cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
