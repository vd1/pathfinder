You are correcting an earlier presentation edit of an accepted mathematics
paper. Above you have the accepted manuscript (for reference only), the
findings of a fresh check, the current manuscript and its BibTeX file.

Resolve the findings by adding definitions and rewording only:
- bind a symbol by a new sentence or by words added to the sentence that
  first uses it;
- explain a concept by a one-line definition;
- restore the accepted manuscript's wording, or delete text the earlier edit
  added, where a finding says that text changed the meaning or claims too
  much.
- reword a sentence a finding of kind "unclear" quotes, so that it says the
  same thing clearly.
Never add a statement about cited work, a citation, an author's name, a
constant or number, a reference to a numbered theorem or section, a
displayed formula, or a new claim. Do not change the wording of any other
sentence the accepted manuscript has, except to restore it. A check compares your
manuscript with the current one sentence by sentence and discards the whole
correction if it does any of these.

If a finding cannot be resolved within these rules, leave the text and
escalate it. Keep the preamble, comments and citation keys as they are. The
result must compile.

Return exactly these blocks and nothing else:
===PAPER===
the complete corrected LaTeX source
===REPORT===
one JSON object: {"changelog": ["location: what changed, for which finding"],
 "title": null, "findings": [],
 "escalations": [{"where": "location", "issue": "the finding you could not resolve and why"}]}
