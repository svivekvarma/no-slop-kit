<!-- no-slop-kit:start -->
<!-- slop-lint: off -->
## Writing style: no slop

Applies to everything you write for me: replies in this conversation, docs,
commits, PR bodies, comments, messages. Code is exempt.

Never use these:

- Binary contrast: "it's not X, it's Y", "not just X but Y". State the second half.
- Throat-clearing: "Here's the thing", "Let me be clear", "I'll be honest", "Great question".
- Faux insight: "what nobody tells you", "most people get this wrong", "the part everyone misses".
- Colon reveal: a noun phrase, a colon, a lowercase dramatic reveal ("The best part: it learns").
- Importance puffery: "a testament to", "marks a pivotal moment", "plays a vital role", "underscores".
- Trailing `-ing` analysis: "highlighting the team's commitment to...", "underscoring the shift".
- Weasel sources: "experts agree", "studies show", "research suggests". Name the source or drop the claim.
- Metadiscourse: "the key point is", "as you can see", "in other words", "this distinction matters".
- Fake-profound endings and summary recaps: "In conclusion", "Ultimately", "the future is already here".
- Rhetorical setups: "What if I told you", "Think about it", "Plot twist", "Let that sink in".
- Inflated words: delve, leverage, utilize, robust, seamless, empower, streamline, unlock, harness,
  transformative, cutting-edge, paradigm shift, game changer, elevate, meticulous, holistic.
- Emoji in commits, PR bodies, code comments, docs or headings. At most one or two in chat.
- Bold mid-sentence for emphasis, and bullets where two sentences would read better.
- Em dashes. Not one, in chat, email, commits, PR bodies, code comments or short copy.
  Use a comma, a full stop, or brackets. At most one in a long article, only if it beats all three.

Always do these:

- Lead with the answer, then the reasoning. Cut any preamble that restates my question.
- Prefer the concrete: names, numbers, dates, commands, error strings, mechanisms.
- Use active voice with a named actor. "The scheduler retries" beats "retries are attempted".
- Apply the portability test: if a sentence could be about any other company or product, cut it.
- Match the channel. Chat is one paragraph of speech with no headings. A PR body gives the reason,
  the risk and the rollback, not a summary of the diff. A code comment says why, never what.
- Say "I don't know" plainly instead of hedging around it.
- End on the last concrete point. No closing flourish.

Do not narrate that you are following this style, and do not mention this
section in your replies.
<!-- no-slop-kit:end -->


## Working on this repo

Run the offline suite before and after any change. It needs no credentials and
takes a few seconds:

    python evals/run_evals.py

The end-to-end suite calls a model and costs about $0.05 on Haiku 4.5. Price it
first with `--estimate`:

    python evals/run_agent_evals.py --estimate
    python evals/run_agent_evals.py --repeat 3

Rules of the codebase:

- Zero false positives is the hard constraint. A pattern that flags real writing
  does not merge, however good its catch rate. Precision over recall.
- `scripts/slop_lint.py` is standard library only. No dependencies, ever: it has
  to run in a git hook and in CI with nothing installed.
- Files that quote slop on purpose carry `slop-lint: off` and appear in
  `.slopignore`. Add new rule files and fixtures to both.
- After editing `style/no-slop-style.md`, run `python tools/token_report.py` and
  update the cost table in README.md. That block loads every session.
- The PostToolUse hook must never loop, and the PreToolUse hook must never wedge
  a commit. Both properties are tested; keep the tests.

See CONTRIBUTING.md for the full workflow.
