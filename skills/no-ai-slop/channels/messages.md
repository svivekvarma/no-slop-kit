---
channel: messages
slop-lint: off
---

# Channel: messages

Slack, Teams, Discord, DMs, SMS.

Chat is speech. The failure mode here is not ugliness, it is a message that
looks like a memo: headings, bold labels, a bulleted summary and a closing line,
where a colleague would have typed one sentence.

## Extra rules

- **No headings. No bold section labels. No closing summary.** If the draft has `**Context:**` and `**Ask:**` in a chat message, that is the slop.
- **Usually one paragraph.** Under 60 words for most messages. Past 120 it belongs in a doc with a link.
- **Bullets only for a genuine list of three or more parallel items**, never as a way to structure a two-sentence thought.
- **Lead with the ask or the answer.** In chat the first line is the whole message, because that is what shows in the notification.
- **Keep contractions, lowercase starts and sentence fragments** if that is how the person types. Chat is the channel where over-polishing is most obvious.
- **No em dashes.** Nobody types an em dash in Slack.
- **Say the number.** "deploy is down, ~15 min" beats "there appears to be an issue with the deployment".
- **Thread it instead of prefacing it.** Do not write "quick context before my question" and then three paragraphs. Ask, then add context in the thread.

## Channel-specific slop

| Slop | Fix |
| --- | --- |
| "Hi team! 👋 Hope everyone's having a great week!" then the actual point | Lead with the point. |
| "**Summary:** ... **Next steps:** ..." in a DM | One paragraph. |
| "Just wanted to quickly check in on the status of..." | "any update on the retry budget?" |
| "Circling back to sync on this offline." | "can we talk about this at 2?" |
| "Great question! Let me break this down." | Answer it. |
| "Does that make sense?" appended to everything | Delete. Ask only when you actually doubt it landed. |
| A tidy three-bullet answer to a yes/no question | "yes, but only on staging." |

## Keep

Keep "no idea, asking Priya". Keep the typo. Keep the lowercase. Keep the
single-word answer. A message that reads as typed by a person in 10 seconds is
correct for this channel even when it would be wrong anywhere else.
