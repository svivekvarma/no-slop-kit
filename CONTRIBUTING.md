<!-- slop-lint: off -->

# Contributing

The linter is only as good as its pattern catalog, and the catalog is wrong in
both directions. Reports of either kind are the most useful thing you can send.

## Before anything else

```sh
python evals/run_evals.py
```

182 checks, no credentials, no cost, a few seconds. It must pass before and
after your change.

## False positives matter more than misses

A linter that flags good writing gets switched off, and then it catches
nothing. The suite holds the false-positive rate at zero and a PR that raises
it will not be merged, however good its catch rate.

Found one? Add the sentence to a file in `evals/fixtures/clean/` with
`max_findings: 0` in the front matter, run the suite, and open the issue with
the failure output. That is a complete bug report.

There is a worked example in the history: the linter counted `→` as an emoji,
so `'recieve' → 'receive'` in a PR title scored 50/100. Arrows are ordinary
technical typography. The fix was to drop the arrows block from the emoji
character class and add `evals/fixtures/clean/typography.md` so it cannot come
back.

## Reporting a miss

Add the sentence to `evals/fixtures/upstream_examples.tsv`:

```
rule-id	channel	the sentence that should have been caught
```

Tab-separated. If you believe no regex could catch it without false positives,
put it in `known_misses.tsv` instead, with a category. Those lines are asserted
to be **missed**, so they document the boundary between what regex can do and
what needs the model.

A failing test with a real example is a complete contribution. You do not have
to write the regex.

## Adding a pattern

1. Add a `Rule(...)` to `RULES` in `scripts/slop_lint.py`. Use `severity` 3 for
   a signature pattern, 2 for usually-slop, 1 for needs-judgement.
2. If the pattern has legitimate uses, give the rule a `reject` regex.
   `colon-reveal` does this: it exempts a clause with a real main verb, so
   "The fix took four lines: cap attempts at three" stays clean while
   "The best part: it learns" does not.
3. Add at least one positive example to `upstream_examples.tsv`.
4. Add a near-miss to `evals/fixtures/clean/` that must **not** fire.
5. Run the suite. Zero false positives, or it does not merge.

Prefer precision. A pattern that catches 60% of a slop type with no false
positives is worth more than one that catches 95% and flags real writing,
because the second one trains people to ignore the output.

## Adding a channel

Four things, and the suite checks that all four exist:

1. `skills/no-ai-slop/channels/<name>.md`, holding only what differs from the
   shared rules. Keep it short; it loads into context when the skill runs.
2. A `Channel(...)` entry in `CHANNELS` in the linter, with its em dash budget,
   emoji budget, heading policy, word guide, and which rules to `mute` or
   `amplify`.
3. A row in the router table in `skills/no-ai-slop/SKILL.md`.
4. A case in `evals/agent_cases.json`.

Add a path hint to `CHANNEL_PATH_HINTS` if the channel maps to a recognisable
file path.

## Editing the style block

`style/no-slop-style.md` loads into every session for every user, so a new line
has to be worth its tokens. After editing:

```sh
python tools/token_report.py
```

Put the new number in the README cost table. If the block grows past roughly
800 tokens, something should come out.

## Changing the hooks

Both hook contracts are tested end to end in `run_evals.py`. Two properties are
not optional:

- **The `PostToolUse` hook must never loop.** It reports once per content hash,
  so the agent fixing a file cannot trigger another round.
- **The `PreToolUse` hook must never wedge a commit.** It blocks once on
  signature slop; the same command run again goes through.

If you change either, keep the tests that prove those properties.

## Prose in this repo

The repo lints itself, minus the files that quote slop on purpose. Those carry
`slop-lint: off` in their front matter and appear in `.slopignore`. If you add
a rule file or a fixture, add it to both.

## End-to-end suite

```sh
python evals/run_agent_evals.py --estimate
python evals/run_agent_evals.py --repeat 3
```

About $0.05 a run on Haiku 4.5. It needs an API key. If you could not run it,
say so in the PR and a maintainer will.

## Attribution

The slop catalog comes from [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop)
(MIT). If you move content between this repo and upstream, keep the provenance
headers on `SKILL.md` and `eval.md` accurate, and update [NOTICE](NOTICE).
Contributions are accepted under the MIT license.
