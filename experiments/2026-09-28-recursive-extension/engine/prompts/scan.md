You are judging one candidate pairing of two research papers, Q and P,
drawn from two different corpora. Judge only from the text below. Do not
browse and do not assume content beyond it.

Decide whether this pairing implies a research connexion worth pursuing:
something one paper supplies that the other could use, test, extend or
contradict, concrete enough that somebody could act on it.

First name the connexion. What claim, method, mechanism, derivation,
comparison or experiment links Q to P, what would be built or run, and
what result would establish or refute it. If nothing follows from the
pair beyond "both papers exist", say so and score accordingly.

Then score two independent axes, each an integer from 0 to 100.

feasibility: could that connexion be investigated by a competent group
with methods and resources that exist today? Ignore whether the result
would be interesting.
  0   no coherent connexion; nothing to investigate
  25  well defined but needs tools, data or theory that do not yet exist
  50  possible in principle but demanding
  75  achievable with ordinary effort; the pieces are in the two papers
  100 small and direct; plausibly done within days

gain: what would be learned that is not already known, specifically
because Q and P are brought together? Ignore difficulty.
  0   nothing new; already known or immediate from either paper alone
  25  incremental confirmation or minor extension
  50  substantive but local
  75  resolves a live uncertainty or materially advances understanding
  100 decisive; revises a central claim or opens a new line of work
If the same connexion could be made with almost any paper of P's kind,
nothing about P is doing work: cap gain at 50.

Score the strongest connexion you can construct, not the average reading.
Use the full range. Do not inflate to be safe; thresholds are applied
downstream. Most pairs score low on at least one axis, and that is not a
criticism of either paper.

Output exactly one JSON object and nothing else, no code fences:
{"feasibility": 0, "gain": 0, "connexion": "one sentence naming it",
 "rationale": "two or three sentences saying why each number is what it is"}

## Q

Title: {{Q_TITLE}}

{{Q_BODY}}

## P

Title: {{P_TITLE}}

{{P_BODY}}
