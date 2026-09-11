---
slop-lint: off
---

<!--
Provenance: the Editing principles, Words to cut, Patterns to cut and Final read
sections are reproduced from petergyang/no-ai-slop (MIT, Copyright (c) 2026
Peter Yang). The Channel checks section is new to no-slop-kit. See NOTICE.
-->

# No slop eval

Use this after the rewrite. Answer each check with pass or fail. If any check fails, fix the draft before returning it.

For detect requests, make sure the response names each pattern found with a quoted line and a short fix, without rewriting the draft.

## Editing principles

1. Does the edit preserve the user's point without adding claims, examples, stats, quotes or opinions?
2. Does it preserve the writer's distinctive vocabulary, cadence, bluntness, humor, uncertainty, digressions and level of polish?
3. Does it leave strong human sentences alone instead of rewriting them for consistency or making every paragraph equally tidy?
4. Is the amount of cutting proportional to the actual slop, with no aggressive compression that strips out character?
5. Does the draft lead with what the reader needs while keeping personal setup that adds context, tension or character?
6. Are points front-loaded where that improves clarity without forcing every unit into the same structure?
7. Do sentences earn their place, with concrete facts, protected details and direct verbs where the draft supports them?
8. Does every generic sentence pass the portability test, or was it cut or made specific to this subject?
9. Does the draft use active voice with human subjects where possible?
10. Does the edit keep useful edge and preserve structure unless the structure was hurting the piece?
11. Are genuinely tangled sentences fixed while clear spoken cadence, fragments and changes in pace remain intact?

## Words to cut

1. Are banned words, filler phrases, often-empty adverbs and inflated claims removed unless quoted as examples?

## Patterns to cut

1. Are binary contrasts, negative listings, rhetorical setups and throat-clearing openers removed?
2. Are faux-insight setups, colon reveals, superficial analysis, fake-strong verbs, synonym cycling, dramatic fragments and robotic rhythm fixed?
3. Are importance puffery and weasel attribution replaced with plain facts and named sources, or flagged for the user when no source exists?
4. Is interpretive metadiscourse removed, including authorial metacommentary, reader guidance, emphasis markers and redundant glossing?
5. Are fake-profound kicker lines deleted instead of rewritten into better metaphors?
6. Are summary-recap endings cut so the piece ends on a concrete point, takeaway or next action?
7. Is formatting slop removed: emoji headings, decorative bold, bullets that should be prose, headers over tiny sections?
8. Are colons sentence case unless grammar, a proper noun, a title or code requires otherwise?
9. Are em dashes used sparingly: usually none in short copy, and only 1-2 in longer drafts when they clearly help?

## Channel checks

1. Was a channel chosen, and does the edit follow that channel's file in `channels/`?
2. Does the draft respect the channel's length guide, or is the overrun justified by content?
3. Does it respect the channel's formatting rules: headings, bullets, bold, emoji and em dashes?
4. For `technical-docs`: does it answer the reader's question in the first sentence, name the actor in each instruction, and say what breaks?
5. For `articles-and-blogs`: is the kicker deleted rather than rewritten, and is there no summary-recap paragraph?
6. For `email`: is the ask and its deadline in the first two sentences?
7. For `messages`: is it one paragraph of speech with no headings or bold labels?
8. For `social-posts`: are both the hook line and the closing line gone?
9. For `social-comments`: does the comment add a fact, a disagreement, a counterexample or a question rather than restating the post?
10. For `code-comments`: does every remaining comment explain why rather than narrate what?
11. For `pull-requests`: does the body give the reason, the risk and the rollback rather than summarising the diff?
12. For `review-comments`: does each comment say whether it blocks and propose the concrete change?

## Linter cross-check

1. If `scripts/slop_lint.py` was run, was every `slop` and `likely` finding either fixed or consciously kept for a stated reason?
2. Were any edits made only to satisfy the linter, with no improvement to the writing? If so, revert them.
3. Was the linter's score left out of the response, or reported only as a rough signal rather than a measure of quality?

## Final read

1. Does the draft avoid robotic symmetry, repeated sentence shapes and stacked punchy fragments?
2. Would the writer recognize the edited draft as their own voice?
3. Would the edited draft sound natural if read to a sharp colleague?
4. Does the final output include the full edited draft and a short **What changed** section?
5. For detect requests, does the response name each pattern with a quoted line and a short fix, without rewriting, scoring or claiming AI authorship?
