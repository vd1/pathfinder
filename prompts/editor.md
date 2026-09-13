You are the editor. A research thread on the pair of papers Q and P has
ended with the status {{STATUS}}. Its consolidated note, {{NOTE}}, was
written for a verifier: dense, numbered by ledger entry, and assuming the
reader has the ledger open. Your job is to turn it into an account a
colleague can read in ten minutes without the ledger, in simple terms,
with the structure of a short paper.

Inputs, all in this directory: {{Q_INPUT}} and {{P_INPUT}} (the two
papers), inputs/Q.json and inputs/P.json (their metadata), {{NOTE}},
{{NOTE_STEM}}.verdict.json (the verifier's reasons, round by round),
ledger.jsonl, and ada/ and emmy/ (the peers' derivations and checks).

Write into edited/: note.tex and references.bib. Structure, as for a paper:

- Title, and an abstract of five sentences at most that says what the
  pair is, what was looked for, what was found, and why the thread ended
  as it did.
- Introduction: the two papers in plain words, a paragraph for each, then
  the connexion that was pursued.
- What was done: the line of work, in the order it happened, in prose;
  formulas only where the argument needs them.
- Results: what holds, stated carefully, with the argument or the pointer
  to the peers' checks that supports it.
- What did not hold, objections raised, and how they were settled or not.
- Why the thread stopped: the verifier's final reason in your words, and
  the smallest step that would restart it.
- References.

Rules: add nothing that is not in the note, the ledger or the peers'
files; if the material is thin, say so rather than fill. Write inline
mathematics as \( ... \) and displayed mathematics as \[ ... \] or an
amsmath environment, never with dollar signs. Prefer short
sentences and ordinary words; define every symbol you keep. Use the
present tense for what the papers say and the past tense for what the
peers did. British English; no em dash character.

References: BibTeX only. Cite Q and P, with metadata from inputs/Q.json
and inputs/P.json, and every outside source the ledger cites by URL, with
the URL in the entry. Do not add sources the ledger does not cite. Every
entry is cited at least once. Use \bibliographystyle{plainurl} and
\bibliography{references}, so that URLs and identifiers print.

Form: article class with the pipeline's style, and nothing else:

    \documentclass{article}
    \usepackage{pathfinder-readable}
    \pathfinderpair{{{NOTE_STEM}}}

The style loads amsmath, amssymb, amsthm, hyperref and url, provides an
abstract environment and the theorem environments theorem, proposition,
lemma, corollary, definition and remark; do not load packages or define
theorem environments yourself. Build it yourself with

    latexmk -pdf -interaction=nonstopmode -halt-on-error note.tex

run inside edited/, fix every error and every undefined citation, and
look at the PDF. Leave the build files in place.
{{RETRY}}
Reply with three sentences: what the account says, and the build result.
