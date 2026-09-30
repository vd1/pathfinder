"""Failure classes for model calls, from the transport outcome and the error parsed out of the
provider's structured events (turn.failed, error, result with is_error). Never from the stderr of a
running agent or its message text: those carry tool output and research prose, which mention
capacity, authentication and limits for reasons of their own.

scope says how far a failure reaches: "call" (retrying later may work), "pair" (this pair's content is
the problem) or "campaign" (every further call will fail the same way until something outside the
engine changes: a usage limit resets, a key is replaced, a CLI is repaired)."""
from __future__ import annotations
import re
from dataclasses import dataclass

SCOPES = {
    "quota": ("campaign", False), "auth": ("campaign", False), "launch": ("campaign", False),
    "refusal": ("pair", False), "input_too_large": ("call", False),
    "rate": ("call", True), "no_session": ("call", True), "timeout": ("call", True),
    "undiagnosed": ("call", False),
}
CLASSES = tuple(SCOPES)

RULES = (
    ("quota", re.compile(r"usage limit|session limit|hit your limit|insufficient_quota|quota exceeded|credit balance", re.I)),
    ("auth", re.compile(r"\b401\b|unauthori[sz]ed|incorrect api key|invalid api key|authentication failed|missing environment variable", re.I)),
    ("input_too_large", re.compile(r"input_too_large|input too large|exceeds the maximum length|context length|prompt is too long", re.I)),
    ("refusal", re.compile(r"flagged for possible|safeguards flagged|content filter|usage polic", re.I)),
    ("rate", re.compile(r"\b429\b|rate limit|too many requests|at capacity|overloaded|\b503\b|service unavailable", re.I)),
)
RESET = re.compile(r"try again at ([^\n]+?)\.?\s*$|resets? (?:at )?([0-9][^\n,.]*)", re.I | re.M)
OUTCOMES = {"launch failed": "launch", "no session": "no_session", "timeout": "timeout"}


@dataclass(frozen=True)
class Failure:
    cls: str
    scope: str
    retry: bool
    reset_at: str | None = None

    def record(self) -> dict:
        return {"class": self.cls, "scope": self.scope, "retry": self.retry, "reset_at": self.reset_at}


def classify(outcome: str | None, error: str | None, extra_rules=()) -> Failure | None:
    """The failure a receipt records, or None for a completed call or an ordinary admission refusal.
    extra_rules, a deployment's (class, compiled pattern) pairs, are tried before the built-in rules."""
    for name, _ in extra_rules:
        if name not in SCOPES:
            raise ValueError(f"unknown failure class {name!r}; expected one of {', '.join(CLASSES)}")
    message = error or ""
    if outcome in (None, "completed") and not message:
        return None
    rules = (*extra_rules, *RULES)
    if outcome == "refused":
        if not RULES[2][1].search(message):
            return None
        cls = "input_too_large"
    elif outcome in OUTCOMES:
        cls = OUTCOMES[outcome]
    else:
        cls = next((name for name, pattern in rules if pattern.search(message)), "undiagnosed")
    scope, retry = SCOPES[cls]
    reset = None
    if cls == "quota":
        match = RESET.search(message)
        reset = (match.group(1) or match.group(2)).strip() if match else None
    return Failure(cls, scope, retry, reset)


def rules_for(campaign) -> tuple:
    """A deployment's own failure rules, compiled and checked, or () when the campaign names none."""
    from . import extensions
    spec = extensions.load(campaign, "failure_rules")
    if spec is None:
        return ()
    compiled = tuple((name, re.compile(pattern, re.I)) for name, pattern in spec)
    for name, _ in compiled:
        if name not in SCOPES:
            raise ValueError(f"unknown failure class {name!r} in failure_rules; expected one of {', '.join(CLASSES)}")
    return compiled
