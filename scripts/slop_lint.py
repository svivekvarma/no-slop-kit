#!/usr/bin/env python3
"""Deterministic AI-slop detector for prose.

Two modes:

  CLI   python slop_lint.py FILE [FILE ...] [--channel NAME] [--format text|json]
  Hook  echo '<hook event JSON>' | python slop_lint.py --hook

The hook mode dispatches on hook_event_name:

  PostToolUse  Write/Edit to a prose file  -> report findings as additionalContext
  PreToolUse   Bash git commit / gh pr / gh issue
               -> lint the message text before it is published

Standard library only. No network, no model, no API key. Detection therefore
costs zero model tokens; only the findings it reports enter Claude's context.

Pattern catalog derives from the rules in petergyang/no-ai-slop (MIT).
See NOTICE for provenance.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shlex
import sys
import tempfile
from dataclasses import dataclass, field

VERSION = "1.0.0"

for _stream in (sys.stdout, sys.stderr):
    try:  # Windows consoles default to cp1252 and choke on quoted emoji.
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROSE_EXTS = {".md", ".mdx", ".markdown", ".txt", ".rst"}

# Scores are findings per 100 words. Below this many words the denominator is
# held here, so a short message is not scored on a sample of one sentence.
SHORT_TEXT_FLOOR = 60

# ---------------------------------------------------------------------------
# Pattern catalog
# ---------------------------------------------------------------------------
# severity: 3 = signature slop, 2 = usually slop, 1 = check it in context


@dataclass
class Rule:
    rid: str
    severity: int
    label: str
    fix: str
    pattern: str
    flags: int = re.IGNORECASE
    reject: str | None = None   # if this matches inside a hit, drop the hit
    regex: re.Pattern | None = field(default=None, repr=False)
    reject_re: re.Pattern | None = field(default=None, repr=False)

    def compiled(self) -> re.Pattern:
        if self.regex is None:
            self.regex = re.compile(self.pattern, self.flags)
        return self.regex

    def rejects(self, text: str) -> bool:
        if self.reject is None:
            return False
        if self.reject_re is None:
            self.reject_re = re.compile(self.reject, re.IGNORECASE)
        return self.reject_re.search(text) is not None


# A colon reveal is a verbless noun phrase, then a colon, then a dramatic
# lowercase payoff ("The best part: it learns"). A clause with a real main verb
# before the colon is ordinary prose ("The fix took four lines: cap attempts at
# three"), so the main verb vetoes the finding. A verb inside a relative clause
# does not, because "The detail that makes it work: ..." is still a reveal.
COLON_MAIN_VERB = (
    r"(?<!that )(?<!which )(?<!who )\b(?:"
    r"is|was|are|were|be|been|has|have|had|took|take|takes|gets|get|got|"
    r"means|mean|costs|cost|cuts|cut|adds|add|needs|need|requires|require|"
    r"does|do|did|went|go|goes|dropped|drop|drops|runs|run|ran|lets|let|"
    r"makes|make|made|shows|show|showed|comes|come|came|said|says|say|"
    r"will|can|could|should|would|may|might|must|gives|give|gave|uses|use|used"
    r")\b"
)


def _alt(*words: str) -> str:
    return "|".join(re.escape(w) for w in words)


BANNED_WORDS = [
    "delve", "delves", "delving", "foster", "fostering", "leverage", "leverages",
    "leveraging", "utilize", "utilizes", "utilizing", "facilitate", "facilitates",
    "empower", "empowers", "empowering", "streamline", "streamlines", "streamlining",
    "robust", "cutting-edge", "paradigm shift", "game changer", "game-changer",
    "tapestry", "realm", "beacon", "multifaceted", "meticulous", "meticulously",
    "intricate", "intricacies", "paramount", "transformative", "elevate", "elevates",
    "elevating", "embark", "embarks", "embarking", "supercharge", "supercharges",
    "harness", "harnesses", "harnessing", "ever-evolving", "ever-changing",
    "seamless", "seamlessly", "unlock", "unlocks", "unlocking", "unleash",
    "unleashes", "plethora", "myriad", "bustling", "testament", "holistic",
    "synergy", "synergies", "best-in-class", "world-class", "next-level",
    "this is huge", "this changes everything",
]

EMPTY_PHRASES = [
    "it's worth noting", "it is worth noting", "it's important to note",
    "it is important to note", "at the end of the day", "when it comes to",
    "at its core", "in today's world", "in today's fast-paced", "in the age of",
    "in the world of", "the reality is", "the truth is", "in terms of",
    "with regard to", "with respect to", "going forward", "in this article",
    "in this post", "let's dive in", "let's dive into", "dive deep into",
    "needless to say", "it goes without saying", "the fact of the matter is",
    "first and foremost", "last but not least",
]

EMPTY_ADVERBS = [
    "just", "literally", "honestly", "simply", "actually", "truly",
    "fundamentally", "importantly", "crucially", "inherently", "inevitably",
    "arguably", "essentially", "basically", "certainly", "undoubtedly",
]

WEAK_VERB_PHRASES = [
    "made a decision", "make a decision", "has the ability to", "have the ability to",
    "serves as a", "serve as a", "serves as the", "plays a role in", "play a role in",
    "provide assistance", "provides assistance", "conduct an analysis",
    "take into consideration", "takes into consideration", "is responsible for",
    "are responsible for", "give consideration to", "perform an evaluation",
    "make an improvement", "reach a conclusion", "is able to", "are able to",
    "in order to", "a wide range of", "a variety of", "a number of",
]

# Pictographs only. The arrows block (U+2190-U+21FF) is deliberately excluded:
# "'recieve' -> 'receive'" and "40min -> 4min" are ordinary technical
# typography, and counting them as emoji penalised clean prose.
EMOJI = (
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F000-\U0001F0FF"
    "\U00002B00-\U00002BFF"
    "\U0000FE0F"
)

RULES: list[Rule] = [
    Rule("binary-contrast", 3, "Binary contrast",
         "State the second half directly.",
         r"\b(?:it(?:'s|s| is)|this(?:'s| is)|that(?:'s| is)|the (?:question|point|problem|issue|answer|goal|real \w+)(?:'s| is| isn't| is not))\b"
         r"[^.!?\n]{0,40}?\b(?:not|isn't|is not|aren't|wasn't)\b[^.!?\n]{0,60}?"
         r"(?:[,.]|\bbut\b)\s*(?:it(?:'s|s| is)\b|it's\b|its\b|\bbut\b)"),
    Rule("binary-contrast", 3, "Binary contrast",
         "State the second half directly.",
         r"\bnot (?:just|only|merely|simply) [^.!?\n]{0,50}?\bbut (?:also )?\b"),
    Rule("binary-contrast", 3, "Binary contrast",
         "State the second half directly.",
         r"\b(?:isn't|is not|aren't|wasn't|won't be) (?:about|a|an|the) [^.!?\n]{0,40}?[,.]\s*(?:it(?:'s| is)|they(?:'re| are))\b"),
    # Split across a sentence boundary: "This isn't just a launch. It's a shift."
    # The just/only/merely qualifier is required, so ordinary negation followed by
    # a new sentence ("The build isn't green. It is failing on lint.") stays clean.
    Rule("binary-contrast", 3, "Binary contrast",
         "State the second half directly.",
         r"\b(?:is|are|was|were)n[o']?t\s+(?:just|only|merely|simply|really about|about)\s+"
         r"[^.!?\n]{0,45}[.!?]\s+(?:It|They|That|This)(?:'s|'re)\b", 0),

    Rule("throat-clearing", 3, "Throat-clearing opener",
         "Cut it and state the point.",
         r"(?:^|[.!?]\s+|\n)\s*(?:" + _alt(
             "Here's the thing", "Here's what I mean", "Here's the deal",
             "Let me be clear", "Let's be clear", "Let me be honest",
             "I'll be honest", "To be honest with you", "Let's be honest",
             "Make no mistake", "The uncomfortable truth is",
             "Here's what I've learned", "Let me explain", "Buckle up",
             "Spoiler alert", "Real talk",
             # Email and chat openers that do the same job.
             "I hope this email finds you well", "Hope this finds you well",
             "Hope you're doing well", "Hope you're well",
             "I wanted to reach out", "I just wanted to reach out",
             "I wanted to quickly", "Just wanted to", "Just circling back",
             "Just following up", "Per my last email", "As per my last",
             "Great question", "Good question", "That's a great question",
             "Thanks for reaching out", "Hi team", "Hey team",
             "Let me break this down", "Let me walk you through",
         ) + r")\b"),

    Rule("faux-insight", 3, "Faux-insight setup",
         "Cut the setup; let the claim stand alone.",
         _alt(
             "what nobody tells you", "what no one tells you",
             "what most people get wrong", "what everyone gets wrong",
             "the part everyone misses", "the part most people miss",
             "this is the part most people skip", "here's the secret",
             "here's what nobody", "few people realize", "most people don't realize",
             "nobody talks about", "no one talks about", "the dirty little secret",
             "what they don't tell you", "hot take",
             "most people get this wrong", "most people get it wrong",
             "everyone gets this wrong", "most teams get this wrong",
             "unpopular opinion", "controversial take",
         )),

    Rule("rhetorical-setup", 3, "Rhetorical setup",
         "Drop it and make the point.",
         _alt(
             "what if I told you", "think about it", "let that sink in",
             "plot twist", "wild, right", "sound familiar", "here's a thought",
             "picture this", "imagine a world where", "ask yourself",
         )),

    Rule("superficial-analysis", 3, "Superficial -ing analysis",
         "Replace with the concrete consequence.",
         r",\s+(?:" + _alt(
             "highlighting", "underscoring", "reflecting", "showcasing",
             "demonstrating", "emphasizing", "signaling", "cementing",
             "illustrating", "reinforcing", "marking", "solidifying",
             "positioning", "paving the way",
         ) + r")\b"),

    Rule("importance-puffery", 3, "Importance puffery",
         "State the fact; let the reader judge.",
         _alt(
             "stands as a testament", "a testament to", "marks a pivotal moment",
             "marks a significant", "plays a vital role", "plays a crucial role",
             "plays a pivotal role", "solidifies its position",
             "underscores its significance", "underscores the importance",
             "cannot be overstated", "speaks volumes", "is a game changer",
             "represents a significant milestone", "ushers in a new era",
             "a new era of", "the dawn of a new",
         )),

    Rule("interpretive-metadiscourse", 2, "Interpretive metadiscourse",
         "Delete the aside or replace it with the supporting fact.",
         _alt(
             "that last part matters", "that part matters more",
             "the key point is", "the key takeaway is", "as you can see",
             "in other words", "this distinction matters", "this matters because",
             "and that's the point", "but here's why that matters",
             "it's important to understand", "make sure you understand",
             "what's interesting is", "what's notable here",
         )),

    Rule("weasel-attribution", 3, "Weasel attribution",
         "Name the source or cut the claim.",
         _alt(
             "experts agree", "experts say", "studies show", "studies suggest",
             "research shows", "research suggests", "industry reports suggest",
             "many argue", "some argue", "many believe", "it is widely believed",
             "widely regarded as", "some say", "critics argue", "data shows that",
             "surveys reveal", "reports indicate", "it is often said",
         )),

    Rule("negative-listing", 3, "Negative listing",
         "Just say what it is.",
         r"\bNot (?:a|an|just|only|about|another)\b[^.!?\n]{0,60}[.!?]\s+Not\b"),

    Rule("dramatic-fragment", 2, "Dramatic fragment",
         "Use a complete sentence.",
         r"(?:^|[.!?]\s+|\n)\s*(?:" + _alt(
             "That's it", "That's the whole thing", "That's the point",
             "Full stop", "Period", "End of story", "Simple as that",
             "And that's okay", "And that's fine", "Not anymore", "Until now",
             "Every. Single. Time",
         ) + r")\s*[.!]"),

    Rule("fake-profound-kicker", 3, "Fake-profound kicker",
         "Delete it; end on the clearest concrete sentence.",
         _alt(
             "the future isn't coming", "the future is not coming",
             "it's already here", "welcome to the future",
             "the future is already here", "the future belongs to",
             "one thing is certain", "only time will tell",
             "the question is no longer whether", "we're just getting started",
             "this is only the beginning", "the rest is history",
             "and that changes everything", "and that changed everything",
             "that changed everything", "nothing will ever be the same",
             "read that again", "let that sink in",
         )),

    Rule("summary-recap", 2, "Summary-recap ending",
         "End on the last concrete point or next action.",
         r"(?:^|\n)\s*(?:\*\*)?(?:" + _alt(
             "In conclusion", "To conclude", "In summary", "To sum up",
             "To summarize", "Ultimately", "Overall", "All in all",
             "At the end of the day", "The bottom line is", "Wrapping up",
             "Final thoughts",
         ) + r")\b"),

    Rule("weak-verb-phrase", 1, "Weak verb phrase",
         "Use a direct verb.",
         r"\b(?:" + _alt(*WEAK_VERB_PHRASES) + r")\b"),

    Rule("passive-agent", 1, "Passive voice with hidden actor",
         "Name who did it.",
         r"\b(?:was|were|is|are|been|being|be)\s+\w+(?:ed|en)\s+by\s+(?:the|a|an|our|their)\b"),

    Rule("hedge-stack", 2, "Stacked hedges",
         "Pick one hedge or none.",
         _alt(
             "may potentially", "could potentially", "might possibly",
             "can potentially", "may possibly", "it seems likely that",
             "there is a possibility that",
             "could we potentially", "might we potentially",
             "I might be missing something", "I may be missing something",
             "I was wondering whether", "I was wondering if",
             "would it make sense to", "could we maybe",
             "I wonder if it might", "perhaps we could consider",
             "it could be argued that", "one could argue",
             "not sure if this is right, but",
         )),

    Rule("banned-word", 2, "Inflated vocabulary",
         "Use the plain word.",
         r"\b(?:" + _alt(*BANNED_WORDS) + r")\b"),

    Rule("empty-phrase", 2, "Empty phrase",
         "Cut it; it delays the point.",
         r"\b(?:" + _alt(*EMPTY_PHRASES) + r")\b"),

    Rule("empty-adverb", 1, "Often-empty adverb",
         "Cut unless it carries real emphasis or uncertainty.",
         r"\b(?:" + _alt(*EMPTY_ADVERBS) + r")\b"),

    Rule("emoji-heading", 3, "Emoji in heading",
         "Remove the emoji; let the words carry the heading.",
         r"(?:^|\n)#{1,6} [^\n]*[" + EMOJI + r"]", re.IGNORECASE),

    Rule("colon-reveal", 2, "Colon reveal",
         "Rewrite as a plain sentence.",
         r"(?:^|\n|[.!?]\s+)(?:The|This|That|One|My|Our|His|Her|Their|A|An)\s"
         r"[a-z][a-z' -]{2,45}?:\s+[a-z]", 0,
         reject=COLON_MAIN_VERB),

    Rule("colon-title-case", 1, "Capital after colon",
         "Use sentence case after a colon unless grammar requires otherwise.",
         r":\s+(?:The|This|That|It|A|An|We|You|Your|They|But|And|If|When|Because)\s+[a-z]", 0),

    Rule("synonym-cycling", 1, "Possible synonym cycling",
         "If the clear word is right, repeat it.",
         r"\b(?:the )?(?:agent|assistant|tool|platform|solution|system|bot)\b"
         r"[^.!?\n]{0,80}[.!?]\s+(?:The )?(?:agent|assistant|tool|platform|solution|system|bot)\b"),

    # Marketing register in documentation. A reader mid-task wants the default
    # value and the failure mode, not a pitch. Kept to phrases with no technical
    # meaning, so genuine terms of art ("drop-in replacement", "cloud-native")
    # are not swept up.
    Rule("marketing-claim", 2, "Marketing claim in documentation",
         "Say what it does and what it costs. Let the reader judge.",
         r"\b(?:" + _alt(
             "out of the box", "out-of-the-box", "under the hood",
             "heavy lifting", "first-class citizen", "batteries included",
             "blazing fast", "blazingly fast", "lightning fast", "lightning-fast",
             "enterprise-grade", "enterprise grade", "industrial-strength",
             "future-proof", "futureproof", "rock solid", "rock-solid",
             "bulletproof", "battle-tested", "turnkey", "one-stop shop",
             "look no further", "the beauty of", "effortless", "effortlessly",
             "painless", "hassle-free", "frictionless", "no-brainer",
             "industry-leading", "state-of-the-art", "bleeding edge",
             "take it to the next level", "next-level", "best of breed",
             "groundbreaking", "revolutionary", "unparalleled", "unmatched",
             "it just works", "incredibly powerful", "insanely fast",
             "supercharged", "turbocharged", "rich set of features",
             "powerful and flexible", "fully-featured", "feature-rich",
         ) + r")\b"),
]


# ---------------------------------------------------------------------------
# Channel profiles
# ---------------------------------------------------------------------------


@dataclass
class Channel:
    name: str
    blurb: str
    em_dash_per_1k: float           # allowed em dashes per 1000 words
    emoji_budget: int               # emoji allowed in body (-1 = unlimited)
    allow_headings: bool
    soft_word_cap: int              # 0 = no cap
    mute: tuple[str, ...] = ()      # rule ids not scored in this channel
    amplify: tuple[str, ...] = ()   # rule ids bumped one severity level


CHANNELS: dict[str, Channel] = {
    "default": Channel(
        "default", "General prose.", 1.5, 0, True, 0),
    "technical-docs": Channel(
        # synonym-cycling is deliberately NOT muted here. Rotating terms for
        # variety is worse in reference material than anywhere else: a reader
        # scanning for "the agent" cannot tell whether "the assistant" two
        # paragraphs down is the same thing.
        "technical-docs", "Reference docs, READMEs, runbooks, ADRs.",
        0.0, 0, True, 0,
        mute=("colon-title-case",),
        amplify=("importance-puffery", "superficial-analysis", "empty-phrase",
                 "binary-contrast", "marketing-claim", "synonym-cycling")),
    "articles-and-blogs": Channel(
        "articles-and-blogs", "Long-form articles, blog posts, newsletters.",
        1.5, 0, True, 0,
        amplify=("fake-profound-kicker", "summary-recap", "faux-insight",
                 "binary-contrast", "throat-clearing", "marketing-claim")),
    "messages": Channel(
        "messages", "Slack, Teams, Discord, DMs, SMS.",
        0.0, 3, False, 120,
        mute=("colon-title-case", "passive-agent"),
        amplify=("throat-clearing", "summary-recap", "interpretive-metadiscourse")),
    "email": Channel(
        "email", "Work email, cold outreach, replies.",
        0.0, 1, False, 250,
        mute=("colon-title-case",),
        amplify=("throat-clearing", "importance-puffery", "empty-phrase")),
    "social-posts": Channel(
        "social-posts", "LinkedIn, X, Threads, Bluesky posts.",
        0.0, 4, False, 220,
        mute=("colon-title-case", "passive-agent"),
        amplify=("binary-contrast", "faux-insight", "fake-profound-kicker",
                 "dramatic-fragment", "rhetorical-setup")),
    "social-comments": Channel(
        "social-comments", "Replies and comments on social posts.",
        0.0, 2, False, 80,
        mute=("colon-title-case", "passive-agent", "summary-recap"),
        amplify=("importance-puffery", "interpretive-metadiscourse",
                 "throat-clearing", "binary-contrast")),
    "code-comments": Channel(
        # A leading "#" here is a Python comment, not a markdown heading, so the
        # heading and heading-emoji rules are muted. Without this every Python
        # comment scored as a structure violation.
        "code-comments", "Inline comments and docstrings.",
        0.0, 0, False, 60,
        mute=("colon-title-case", "summary-recap", "synonym-cycling",
              "dramatic-fragment", "structure-mismatch", "emoji-heading"),
        amplify=("interpretive-metadiscourse", "empty-phrase", "banned-word")),
    "pull-requests": Channel(
        "pull-requests", "PR titles, descriptions, commit messages.",
        0.0, 0, True, 400,
        mute=("colon-title-case", "synonym-cycling"),
        amplify=("importance-puffery", "superficial-analysis",
                 "interpretive-metadiscourse", "summary-recap")),
    "review-comments": Channel(
        "review-comments", "Code review comments and PR replies.",
        0.0, 1, False, 120,
        mute=("colon-title-case", "summary-recap", "passive-agent"),
        amplify=("throat-clearing", "interpretive-metadiscourse",
                 "importance-puffery")),
}

CHANNEL_PATH_HINTS: list[tuple[str, str]] = [
    (r"(?:^|/)\.github/(?:pull_request_template|PULL_REQUEST_TEMPLATE)", "pull-requests"),
    (r"(?:^|/)(?:COMMIT_EDITMSG|PR_BODY|pr-body)", "pull-requests"),
    (r"(?:^|/)(?:docs?|documentation|adr|runbooks?|reference)(?:/|$)", "technical-docs"),
    (r"(?:^|/)(?:README|CONTRIBUTING|CHANGELOG|ARCHITECTURE)", "technical-docs"),
    (r"(?:^|/)(?:blog|posts?|articles?|newsletter|essays?)(?:/|$)", "articles-and-blogs"),
    (r"(?:^|/)(?:emails?|outreach)(?:/|$)", "email"),
    (r"(?:^|/)(?:social|linkedin|twitter|threads)(?:/|$)", "social-posts"),
    (r"(?:^|/)(?:messages?|slack|dms?)(?:/|$)", "messages"),
]


def detect_channel(path: str) -> str:
    norm = path.replace("\\", "/")
    for pattern, channel in CHANNEL_PATH_HINTS:
        if re.search(pattern, norm, re.IGNORECASE):
            return channel
    return "default"


# ---------------------------------------------------------------------------
# Text preparation
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"^([ \t]*)(```+|~~~+)[^\n]*\n.*?(?:^\1?\2[^\n]*$|\Z)",
                      re.DOTALL | re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
LINK_TARGET_RE = re.compile(r"\]\([^)\s]+(?:\s+\"[^\"]*\")?\)")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
COMMENT_OPT_OUT_RE = re.compile(
    r"<!--\s*slop-lint:\s*(off|false|no|skip)\s*-->", re.IGNORECASE)
URL_RE = re.compile(r"https?://\S+")


def _blank_out(match: re.Match) -> str:
    """Replace a span with same-length whitespace so offsets stay valid."""
    return re.sub(r"[^\n]", " ", match.group(0))


def prepare(text: str) -> tuple[str, dict[str, str]]:
    """Strip front matter, code, links and comments. Offsets are preserved."""
    meta: dict[str, str] = {}
    # A README cannot carry YAML front matter without rendering it, so the
    # opt-out is also honoured as an HTML comment anywhere in the first 1KB.
    marker = COMMENT_OPT_OUT_RE.search(text[:1024])
    if marker:
        meta["slop-lint"] = marker.group(1).lower()
    fm = FRONTMATTER_RE.match(text)
    if fm:
        for line in fm.group(1).splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                meta[key.strip().lower()] = value.strip().strip("\"'")
        text = _blank_out(fm) + text[fm.end():]
    for pattern in (HTML_COMMENT_RE, FENCE_RE, INLINE_CODE_RE, LINK_TARGET_RE, URL_RE):
        text = pattern.sub(_blank_out, text)
    return text, meta


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


# ---------------------------------------------------------------------------
# Linting
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    rid: str
    severity: int
    label: str
    fix: str
    line: int
    quote: str


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _quote(text: str, start: int, end: int, pad: int = 24) -> str:
    left = max(0, start - pad)
    right = min(len(text), end + pad)
    snippet = text[left:right].replace("\n", " ")
    snippet = re.sub(r"\s+", " ", snippet).strip()
    if left > 0:
        snippet = "..." + snippet
    if right < len(text):
        snippet = snippet + "..."
    return snippet[:160]


def lint(text: str, channel_name: str = "default") -> dict:
    channel = CHANNELS.get(channel_name, CHANNELS["default"])
    body, meta = prepare(text)
    words = word_count(body)
    findings: list[Finding] = []
    seen: set[tuple[str, int]] = set()

    for rule in RULES:
        if rule.rid in channel.mute:
            continue
        severity = rule.severity + (1 if rule.rid in channel.amplify else 0)
        severity = min(severity, 3)
        for match in rule.compiled().finditer(body):
            hit = match.group(0)
            if not hit.strip():
                continue
            if rule.rejects(hit):
                continue
            # Several rules open with a sentence-boundary group that swallows the
            # whitespace before the phrase, which would otherwise blame the line
            # above. Report the first real character instead.
            start = match.start()
            while start < match.end() and not body[start].isalnum():
                start += 1
            line = _line_of(body, start)
            key = (rule.rid, line)
            if key in seen:
                continue
            seen.add(key)
            findings.append(Finding(
                rule.rid, severity, rule.label, rule.fix, line,
                _quote(body, start, match.end())))

    findings.extend(f for f in _structural_findings(body, words, channel)
                    if f.rid not in channel.mute)
    findings.sort(key=lambda f: (-f.severity, f.line))

    weights = {3: 6.0, 2: 3.0, 1: 1.0}
    raw = sum(weights[f.severity] for f in findings)
    # Density needs a denominator floor. Without one a single em dash in a
    # 16-word Slack message scores 0, which is both useless and wrong: short
    # copy is the normal case in half these channels, and one finding in it is
    # one finding, not a catastrophe.
    denominator = max(words, SHORT_TEXT_FLOOR)
    per_100 = (raw / denominator * 100) if words else 0.0
    score = max(0, round(100 - per_100 * 6))

    return {
        "version": VERSION,
        "channel": channel.name,
        "words": words,
        "findings": [f.__dict__ for f in findings],
        "counts": {
            "signature": sum(1 for f in findings if f.severity == 3),
            "likely": sum(1 for f in findings if f.severity == 2),
            "context": sum(1 for f in findings if f.severity == 1),
        },
        "density_per_100_words": round(per_100, 2),
        "score": score,
        "grade": _grade(score),
        "frontmatter": meta,
    }


def _structural_findings(body: str, words: int, channel: Channel) -> list[Finding]:
    out: list[Finding] = []

    em_dashes = [m for m in re.finditer(r"—|\s--\s", body)]
    allowed = max(0, int(channel.em_dash_per_1k * max(words, 1) / 1000))
    if len(em_dashes) > allowed:
        extra = em_dashes[allowed]
        out.append(Finding(
            "em-dash-density", 2, "Em dashes used as rhythm crutch",
            f"{len(em_dashes)} found, {allowed} budgeted for {channel.name}. "
            "Use commas, periods or parentheses.",
            _line_of(body, extra.start()), _quote(body, extra.start(), extra.end())))

    if channel.emoji_budget >= 0:
        emoji = [m for m in re.finditer(r"[" + EMOJI + r"]", body)]
        if len(emoji) > channel.emoji_budget:
            extra = emoji[channel.emoji_budget]
            out.append(Finding(
                "emoji-density", 1, "Emoji beyond channel budget",
                f"{len(emoji)} found, {channel.emoji_budget} budgeted for "
                f"{channel.name}.",
                _line_of(body, extra.start()), _quote(body, extra.start(), extra.end())))

    if not channel.allow_headings:
        heading = re.search(r"(?:^|\n)#{1,6} \S", body)
        if heading:
            out.append(Finding(
                "structure-mismatch", 2, "Markdown headings in a short-form channel",
                f"{channel.name} reads as plain prose. Drop the headings.",
                _line_of(body, heading.start()),
                _quote(body, heading.start(), heading.end())))
        # A memo wearing a message's clothes: "**Context:** ... **Next steps:** ..."
        # in a Slack message or an email is the signature of generated text.
        # Scoped to short-form channels, where a bold label is never right.
        labels = list(re.finditer(r"(?:^|\n)\s*\*\*[^*\n]{1,40}\*\*\s*:?", body))
        if len(labels) >= 2:
            out.append(Finding(
                "memo-formatting", 2, "Bold section labels in a short-form channel",
                f"{len(labels)} bold labels. A {channel.name} entry is prose, "
                "not a memo. Write it as sentences.",
                _line_of(body, labels[0].start()),
                _quote(body, labels[0].start(), labels[0].end())))

    bold = re.findall(r"(?<![\n*])\*\*[^*\n]{1,60}\*\*(?!\s*:)", body)
    if len(bold) >= 3:
        out.append(Finding(
            "decorative-bold", 1, "Bold sprinkled mid-sentence",
            f"{len(bold)} inline bold spans. Let the words carry the emphasis.",
            1, bold[0][:80]))

    if channel.soft_word_cap and words > channel.soft_word_cap:
        out.append(Finding(
            "over-length", 1, "Longer than the channel usually wants",
            f"{words} words against a {channel.soft_word_cap}-word guide for "
            f"{channel.name}.", 1, ""))

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
    run = 0
    for sentence in sentences:
        if 0 < word_count(sentence) <= 5:
            run += 1
            if run == 3:
                out.append(Finding(
                    "robotic-rhythm", 2, "Stacked punchy fragments",
                    "Three or more very short sentences in a row. Vary the shape.",
                    1, sentence[:80]))
                break
        else:
            run = 0

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    starts = [p.split()[0].lower().strip(".,:*#") for p in paragraphs if p.split()]
    for i in range(len(starts) - 2):
        if starts[i] and starts[i] == starts[i + 1] == starts[i + 2]:
            out.append(Finding(
                "robotic-rhythm", 1, "Repeated paragraph openers",
                f"Three paragraphs in a row start with '{starts[i]}'.", 1, starts[i]))
            break

    return out


def _grade(score: int) -> str:
    if score >= 90:
        return "clean"
    if score >= 75:
        return "minor"
    if score >= 50:
        return "sloppy"
    return "slop"


# ---------------------------------------------------------------------------
# Ignore handling
# ---------------------------------------------------------------------------

DEFAULT_IGNORES = (
    "*/skills/no-ai-slop/*",
    "*/claude-md/*",
    "*/evals/fixtures/*",
    "*/.claude/hooks/*",
    "*/.claude/commands/*",
)


def load_ignores(root: str) -> list[str]:
    patterns = list(DEFAULT_IGNORES)
    path = os.path.join(root, ".slopignore")
    if os.path.isfile(path):
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    return patterns


def is_ignored(path: str, patterns: list[str], root: str = "") -> bool:
    norm = os.path.abspath(path).replace("\\", "/")
    rel = norm
    if root:
        try:
            rel = os.path.relpath(norm, root).replace("\\", "/")
        except ValueError:
            rel = norm
    for pattern in patterns:
        pattern = pattern.replace("\\", "/")
        for candidate in (norm, rel, "/" + rel):
            if fnmatch.fnmatch(candidate, pattern):
                return True
            if pattern.endswith("/") and candidate.startswith(pattern):
                return True
    return False


def opted_out(meta: dict[str, str]) -> bool:
    return meta.get("slop-lint", "").lower() in {"off", "false", "no", "skip"}


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

SEV_TAG = {3: "slop", 2: "likely", 1: "check"}


def render_text(path: str, report: dict, limit: int = 0) -> str:
    lines = [
        f"{path}  [{report['channel']}]  score {report['score']}/100 "
        f"({report['grade']})  {report['words']} words"
    ]
    findings = report["findings"]
    if not findings:
        lines.append("  no slop patterns found")
        return "\n".join(lines)
    shown = findings[:limit] if limit else findings
    for f in shown:
        lines.append(f"  {path}:{f['line']}  [{SEV_TAG[f['severity']]}] "
                     f"{f['rid']} - {f['label']}")
        if f["quote"]:
            lines.append(f"      \"{f['quote']}\"")
        lines.append(f"      fix: {f['fix']}")
    if limit and len(findings) > limit:
        lines.append(f"  ... {len(findings) - limit} more")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hook mode
# ---------------------------------------------------------------------------

HOOK_LIMIT = 8
HOOK_MIN_SEVERITY = 2


def _state_path() -> str:
    """Where the report-once state lives. NO_SLOP_STATE overrides it, which
    keeps test runs from inheriting each other's state."""
    override = os.environ.get("NO_SLOP_STATE")
    if override:
        return override
    return os.path.join(tempfile.gettempdir(), "slop_lint_seen.json")


def _already_reported(key: str) -> bool:
    """Report a given file+content hash once, so fixing a file never re-nags."""
    path = _state_path()
    try:
        with open(path, encoding="utf-8") as handle:
            seen = json.load(handle)
    except Exception:
        seen = {}
    if not isinstance(seen, dict):
        seen = {}
    if key in seen:
        return True
    seen[key] = True
    if len(seen) > 500:
        seen = {key: True}
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(seen, handle)
    except Exception:
        pass
    return False


def run_hook() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(event, dict):
        return 0
    if event.get("hook_event_name") == "PreToolUse":
        return run_pre_bash_hook(event)
    return run_post_write_hook(event)


# Flags whose value is prose that ends up in front of other people.
PROSE_FLAGS: dict[str, str] = {
    "-m": "pull-requests",
    "--message": "pull-requests",
    "--body": "pull-requests",
    "-b": "pull-requests",
    "--title": "pull-requests",
    "-t": "pull-requests",
    "--description": "pull-requests",
    "--notes": "pull-requests",
}

BASH_TRIGGER_RE = re.compile(
    r"\b(?:git\s+commit|git\s+tag|gh\s+pr\s+(?:create|edit|comment)"
    r"|gh\s+issue\s+(?:create|edit|comment)|gh\s+release\s+create)\b")


def extract_bash_prose(command: str) -> list[tuple[str, str]]:
    """Pull (channel, text) pairs out of a git/gh command line."""
    if not BASH_TRIGGER_RE.search(command):
        return []
    is_comment = re.search(r"\b(?:pr|issue)\s+comment\b", command) is not None
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return []
    out: list[tuple[str, str]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        value = None
        channel = None
        if token in PROSE_FLAGS and index + 1 < len(tokens):
            channel = PROSE_FLAGS[token]
            value = tokens[index + 1]
            index += 1
        elif "=" in token:
            flag, _, rest = token.partition("=")
            if flag in PROSE_FLAGS:
                channel = PROSE_FLAGS[flag]
                value = rest
        if value and channel and len(value.split()) >= 3:
            if is_comment:
                channel = "review-comments"
            out.append((channel, value))
        index += 1
    return out


def run_pre_bash_hook(event: dict) -> int:
    """Lint commit messages, PR bodies and review comments before they ship."""
    if event.get("tool_name") != "Bash":
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    payloads = extract_bash_prose(command)
    if not payloads:
        return 0

    lines: list[str] = []
    signature = 0
    for channel, text in payloads:
        report = lint(text, channel)
        actionable = [f for f in report["findings"]
                      if f["severity"] >= HOOK_MIN_SEVERITY]
        if not actionable:
            continue
        signature += sum(1 for f in actionable if f["severity"] == 3)
        lines.append(f"{report['channel']} text scores {report['score']}/100 "
                     f"({report['grade']}):")
        for f in actionable[:HOOK_LIMIT]:
            quote = f' "{f["quote"]}"' if f["quote"] else ""
            lines.append(f"- {f['rid']}:{quote} -> {f['fix']}")
    if not lines:
        return 0

    digest = hashlib.sha256(command.encode("utf-8", "replace")).hexdigest()[:16]
    repeat = _already_reported(f"bash:{digest}")

    header = ("slop-lint checked the prose in this command before it is "
              "published to other people.")
    body = "\n".join([header] + lines)

    # Block once on signature slop so the text can be rewritten, then get out of
    # the way. An unchanged retry is allowed through, so this cannot loop.
    if signature and not repeat:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    body + "\n\nRewrite the message text and run the command "
                    "again. Re-running it unchanged is allowed."),
            }
        }))
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": body,
        }
    }))
    return 0


def run_post_write_hook(event: dict) -> int:
    tool_input = event.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not path or os.path.splitext(path)[1].lower() not in PROSE_EXTS:
        return 0

    root = event.get("cwd") or os.getcwd()
    if is_ignored(path, load_ignores(root), os.path.abspath(root)):
        return 0

    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return 0

    channel = detect_channel(path)
    report = lint(text, channel)
    if opted_out(report["frontmatter"]):
        return 0

    actionable = [f for f in report["findings"] if f["severity"] >= HOOK_MIN_SEVERITY]
    if not actionable:
        return 0

    digest = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]
    if _already_reported(f"{os.path.abspath(path)}:{digest}"):
        return 0

    rel = os.path.relpath(path, root) if root else path
    lines = [
        f"slop-lint: {rel} scores {report['score']}/100 ({report['grade']}) "
        f"on the {report['channel']} profile.",
        "Findings below are from a regex linter, not a judgement about the writing. "
        "Fix the ones that are real slop in context and ignore the rest. "
        "Do not re-run the linter; it re-checks on the next write.",
    ]
    for f in actionable[:HOOK_LIMIT]:
        quote = f' "{f["quote"]}"' if f["quote"] else ""
        lines.append(f"- L{f['line']} {f['rid']}:{quote} -> {f['fix']}")
    if len(actionable) > HOOK_LIMIT:
        lines.append(f"- ... {len(actionable) - HOOK_LIMIT} more of the same kinds")

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "\n".join(lines),
        }
    }))
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="slop_lint.py",
        description="Deterministic AI-slop detector. Zero model tokens.")
    parser.add_argument("files", nargs="*", help="prose files to lint ('-' for stdin)")
    parser.add_argument("--hook", action="store_true",
                        help="read a PostToolUse event on stdin")
    parser.add_argument("--channel", default=None, choices=sorted(CHANNELS),
                        help="channel profile (default: inferred from path)")
    parser.add_argument("--format", default="text", choices=("text", "json"))
    parser.add_argument("--limit", type=int, default=0,
                        help="max findings to print per file (0 = all)")
    parser.add_argument("--min-score", type=int, default=None,
                        help="exit 1 if any file scores below this")
    parser.add_argument("--list-channels", action="store_true")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args(argv)

    if args.hook:
        return run_hook()

    if args.list_channels:
        for name, channel in sorted(CHANNELS.items()):
            print(f"{name:20} {channel.blurb}")
        return 0

    if not args.files:
        parser.print_help()
        return 0

    reports = []
    for path in args.files:
        if path == "-":
            text, label = sys.stdin.read(), "<stdin>"
        else:
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
            except OSError as exc:
                print(f"{path}: {exc}", file=sys.stderr)
                continue
            label = path
        channel = args.channel or detect_channel(label)
        report = lint(text, channel)
        report["path"] = label
        reports.append(report)

    if args.format == "json":
        print(json.dumps(reports if len(reports) > 1 else reports[0], indent=2))
    else:
        print("\n".join(render_text(r["path"], r, args.limit) for r in reports))

    if args.min_score is not None:
        if any(r["score"] < args.min_score for r in reports):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
