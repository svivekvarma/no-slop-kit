---
channel: pull-requests
min_score: 90
max_findings: 0
---

Fix typo in CLI help text: 'recieve' → 'receive'

Corrects a spelling error in the help output. No behaviour change.

Deploy time went from 40 minutes → 4 minutes after the drain step was removed.
The state machine is queued → running → done, with no path back to queued.
