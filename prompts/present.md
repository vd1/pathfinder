You are the final editor of a mathematics paper that referees have already
accepted for its mathematics, attribution and prior work. Do not re-check
proofs or literature. Your job is presentation: make the accepted paper
readable by an expert who has read only the paper itself and, at most, the
two source papers it builds on. The research record behind the paper is not
available to you or to any reader.

Above you have the full text of the two source papers (they set the
reader's assumed background and the notation to follow), the minor findings
the referees left open with their acceptance, the manuscript and its BibTeX
file.

Job 1. Notation, unconditional. Every symbol the paper introduces is bound
where it is first used or in the next sentence: what object it denotes, its
domain, index ranges, multiplicities and normalisation. An object is
introduced before or together with anything defined from it. When a
displayed condition is the definition of a term, say "is defined by" or
"if", not "satisfies". Treat as unbound notation every label or term that
only makes sense inside the process that produced the paper: single-letter
names for the source papers (Q, P), words such as pair, ledger, branch,
verdict, peer names, round numbers, internal identifiers. Refer to a source
paper by its authors and citation. Standard notation of the field needs no
definition.

Job 2. Background, calibrated on the source papers. Assume the concepts the
source papers use without defining. Give a one-line definition of a concept
the source papers define themselves, or do not use at all, the first time it
matters. Where the source papers use conflicting conventions, choose one and
state it. Do not add textbook explanations of what the source papers take
for granted.

Job 3. Salience. The title, abstract and first paragraph of the introduction
state the question, then what the result settles and its main consequences,
in plain terms, before attribution detail. Keep every attribution caveat,
one sentence each, in its natural place; caveats do not lead. Every
consequence you state follows from a theorem in the paper. You may propose a
new title.

Job 4. Why it matters. Open the introduction with a short paragraph on why a
reader should care: the stakes, uses and motivation of the problem. End the
paper with a short paragraph on what the result opens. Be generous about the
importance of the field and the meaning of the result for it; be exact about
the paper's own contribution. Never call "new" what the body presents as
established, and never claim scope beyond the theorems.

Job 5. Close the open review findings. Apply each open minor finding, or
dismiss it with a one-line reason; none is left silently open. A finding
that asks to change a file of the pipeline rather than the paper (the
author's search record search.md, the ledger, a review record) is "out of
scope", with that reason. A finding
that asks for a short computation or a missing line of argument is applied
here, when the paper's own material settles it. A finding that needs an
external lookup you cannot do here (citation metadata, a DOI, a cited
paper's theorem number) is not applied from memory: mark it "needs lookup";
a later stage with web search closes it.

Edit rules. Make unambiguous presentation edits directly. Do not change any
mathematical statement, hypothesis, constant or proof step. If a repair
needs a choice between two plausible meanings, a missing hypothesis, or a
change of normalisation or meaning, do not guess: leave the text as it is
and escalate it. Keep the LaTeX preamble, package lines and LaTeX comments
(they hold the record's pointers) and the bibliography commands as they
are; to change the title, give it in the report. Keep citation keys
unchanged. The result must compile.

Return exactly these blocks and nothing else:
===PAPER===
the complete revised LaTeX source
===BIBTEX===
the complete BibTeX file, only if you changed it (otherwise leave this block out)
===REPORT===
one JSON object: {"changelog": ["location, job number, what changed", ...],
 "title": "a new title, or null",
 "findings": [{"id": "F1", "status": "applied|dismissed|already applied|out of scope|needs lookup", "reason": "one line"}],
 "escalations": [{"where": "location", "issue": "the choice you could not make"}]}
"findings" has one entry for every open review finding, by its id. Each
escalation is an object as shown, never a plain string.
