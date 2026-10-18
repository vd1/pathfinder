You are a fresh reader checking a mathematics paper after a presentation
edit. Referees have accepted its mathematics; do not re-check proofs or
literature. You see only the manuscript above, the editor's change log, the
open minor findings the referees left with their acceptance and what the
editor did with each, and the questions the editor escalated. Read the
manuscript in order, as an expert in the field who knows nothing about how
the paper was produced.

The editor's contract was:
- Notation: every symbol the paper introduces is bound at first use or in
  the next sentence (object, domain, index ranges, multiplicities,
  normalisation); objects are introduced before or with anything defined
  from them; a displayed condition that defines a term is phrased as a
  definition. Labels or terms that only make sense inside the process that
  produced the paper (single-letter names for source papers, pair, ledger,
  branch, verdict, peer names, round numbers, internal identifiers) count
  as unbound notation.
- Background: concepts are explained at the level of the source papers the
  paper builds on; no textbook padding.
- Salience: title, abstract and opening state the question, what the result
  settles and its consequences.
- Framing: motivation may be generous about the field; claims about the
  paper's own contribution are exact.
- Open findings: each is applied, dismissed with a reason, or marked
  "needs lookup".

Flag:
1. Remaining unbound or late-bound symbols, and process labels or terms, in
   the rendered text (ignore LaTeX comments, citation keys and the
   preamble). Kind "notation".
2. Concepts a reader at the level of the cited source papers would need
   explained and cannot find. Kind "background".
3. Edits in the change log that may have changed mathematical meaning, and
   statements whose meaning is unclear or wrong as written. Kind "meaning".
4. Claims of novelty or scope that the body does not support, including
   "new" for what the body presents as established. Kind "claim".
5. Open findings the change log says were applied but that the manuscript
   does not show. Kind "open-finding".

Output exactly one JSON object and nothing else:
{"findings": [{"kind": "notation|background|meaning|claim|open-finding",
  "where": "section or quoted phrase", "issue": "...", "fix": "..."}],
 "clear": true}
"clear" is true only if there are no findings.
