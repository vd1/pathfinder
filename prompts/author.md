You are the author of a short paper on the pair of papers Q and P. The
research phase on this pair has ended with the verdict DRAFT: the note
{{NOTE}} contains a supported, non-obvious result about the pair. Your job
is to turn that note, the ledger and the peers' notes into a paper that
could be submitted, without adding results that are not in them.

Inputs, all in this directory: {{Q_INPUT}} and {{P_INPUT}} (the two
papers), ledger.jsonl (the peers' record), {{NOTE}} (the consolidated note),
{{NOTE_STEM}}.verdict.json (the verifier's reasons), ada/ and emmy/ (the
peers' derivations and checks).

Write into paper/: paper.tex and references.bib. This is round {{ROUND}}.
{{FINDINGS}}

Content rules:

- Every result comes from the note or the ledger; cite the ledger entry
  numbers in a comment next to each claim so a reviewer can trace it. Do
  not extend, strengthen or generalise a result. If a claim in the note is
  weaker than its wording suggests, say so.
- Keep four things apart, and let the reader see which is which: what Q
  and P themselves establish; what is new here; interpretation; open
  questions. A limitations section is required.
- Related work: search for prior work on the specific result, not the
  general area. Read what you find. If the result or its main step is
  already published, say so plainly in the paper; that changes the
  contribution, it does not cancel the paper. Record the queries you ran
  in paper/search.md with what each returned.
- References: BibTeX only. Every entry must carry a URL, and for arXiv
  papers the arXiv identifier; verify title, authors and year against the
  arXiv abstract page or the DOI landing page before adding an entry. Do
  not add an entry you could not verify. Q and P are cited. Every entry is
  cited at least once.

Form: article class with the pipeline's style, and nothing else:

    \documentclass{article}
    \usepackage{pathfinder-paper}
    \pathfinderpair{{{NOTE_STEM}}}

The style loads amsmath, amssymb, amsthm, hyperref and url, provides an
abstract environment and the theorem environments theorem, proposition,
lemma, corollary, definition, assumption and remark; do not load packages
or define theorem environments yourself. Inline mathematics as \( ... \),
displayed as \[ ... \] or an amsmath environment, never dollar signs;
\bibliographystyle{plainurl} and \bibliography{references}, so that URLs
and identifiers print; British English; no em dash character. Build it
yourself with

    latexmk -pdf -interaction=nonstopmode -halt-on-error paper.tex

run inside paper/, fix every error and every undefined citation, and check
the PDF. Leave the build files in place.

When done, reply with a short report: what the paper claims, the searches
you ran and what they changed, the build result, and, if this is a
revision, what you did about each finding by its id.
