<!-- slop-lint: off -->

# Evals

Two suites. One is free and offline, one calls a model.

```sh
python evals/run_evals.py                  # 182 checks, no credentials, no cost
python evals/run_agent_evals.py --estimate # price the second one first
python evals/run_agent_evals.py            # 26 calls, ~$0.05 on Haiku 4.5
```

## run_evals.py

Deterministic. No network, no key. This is what CI runs.

**Ground truth** (`fixtures/upstream_examples.tsv`). Example sentences written
by the upstream author, in `rule-id <TAB> channel <TAB> text` form. The linter
is scored against a definition of slop it was not tuned on, which is the point:
fixtures written by the same person who wrote the patterns prove very little.

**Known misses** (`fixtures/known_misses.tsv`). Genuinely bad writing with no
mechanical tell, asserted to produce **no** findings. If a new pattern starts
catching one of these lines, the suite fails, and you have to decide: keep the
pattern and promote the line to ground truth, or admit the rule is too broad.
This is what keeps "the model catches the rest" from being a slogan.

**Clean corpus** (`fixtures/clean/*.md`). Human prose that must score zero
findings. Front matter sets `channel`, `min_score` and `max_findings`. This is
the most important number in the suite: a linter with false positives gets
switched off, and then it catches nothing.

**Unit and wiring.** Channel routing, code and URL stripping, line-number
accuracy, `.slopignore` globs, front-matter opt-out, commit-message extraction,
both hook contracts end to end, the style installer's idempotency, and the
plugin manifest.

## run_agent_evals.py

End to end. Asks a real model to write, then lints what it wrote.

Each case in `agent_cases.json` runs twice: once with the task prompt alone,
once with the style block as the system prompt. Both go through the same
linter, so grading costs nothing.

A case passes when the styled run:

1. clears the case's `max_score` threshold,
2. scores at least as well as its own baseline, and
3. still contains every string in `must_include`.

Check 3 is the one that matters. Without it a model could score 100 by writing
two words, and the eval would call that a win.

```sh
python evals/run_agent_evals.py --repeat 3        # average 3 samples, less noise
python evals/run_agent_evals.py --models claude-haiku-4-5,claude-sonnet-5
python evals/run_agent_evals.py --channels messages,pull-requests
python evals/run_agent_evals.py --cases pr-body-small
python evals/run_agent_evals.py --backend codex   # or claude
python evals/run_agent_evals.py --save out.json   # keep the generated text
```

Model output varies. A single sample once made a case swing 21 points because
that draft happened to include an emoji. Use `--repeat 3` when the result
matters.

### Cost

Default is the Anthropic API with Claude Haiku 4.5: 26 calls, about $0.05.
`--estimate` prices any configuration without calling anything, and a real run
prints metered token counts from the API.

The `claude` and `codex` backends reload their whole agent harness on every
call, roughly 15k input tokens each against a few hundred for the API. They
cost around 40x more and run much slower. Use them to check the plugin inside a
real harness, not for routine runs.

## Adding a case

A false positive is worth more than a miss. Add the sentence to
`fixtures/clean/` with `max_findings: 0` and run the suite.

For a miss, add a line to `upstream_examples.tsv` with the rule id it should
match. A failing test with a real example is a complete contribution; you do
not need to write the regex.

For a new channel, add a case to `agent_cases.json`. `run_evals.py` checks that
every case names a channel the linter knows.
