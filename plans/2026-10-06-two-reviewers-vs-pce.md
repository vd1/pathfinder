# Two independent paper reviewers against a PCE fact-check, on agQSL's batch 1

**Question.** Does a programme-committee review (two independent reviewers who must both accept) catch what a PCE
fact-check catches, at a third of its calls? If it does, papers keep the two-reviewer stage and PCE is not needed
for them; if the fact-check finds unsupported or weak claims the reviewers passed, PCE earns a place after review.

**Material.** The DRAFT pairs of agQSL's second-campaign batch 1 (Q6P6 to Q25P25), once the batch has finished.

**Arms.**
1. Paper stage with `"paper_reviewers": 2`: `review/reviewer-1` on Claude Opus 5.5, `review/reviewer-2` on
   GPT-6.1 Sol (medium), so the two reviews come from different model families. `paper_rounds` as configured.
2. On each paper both reviewers accepted: one PCE pass (author, archivist, fact-checker, critic, editor) with the
   accepted `paper.tex` and `references.bib` as the baseline, in a scratch copy of the thread, so the record of the
   paper stage is untouched. The fact-checker is on Opus 5.5.

**Measures, per paper.**
- Reviewers: rounds to acceptance; findings per reviewer; findings only one reviewer raised (their disagreement).
- PCE: claims registered; claims classified weak or unsupported, with their basis; whether each was among the
  reviewers' findings (matched by hand on the claim text and location).
- Cost: input tokens and calls per arm (`pathfinder economy`, Claude counted with its cache).

**Decision rule.** If the PCE fact-check finds no weak or unsupported claim the reviewers missed on most papers,
two reviewers are enough. If it finds such claims on more than a quarter of the papers, add a PCE pass after
acceptance for papers.

**Order.** After batch 1: release the engine with `paper_reviewers`, refreeze agQSL's engine, set the two routes
and `paper_reviewers: 2` in agQSL's `campaign.json` (the next run needs `--accept-change`), run the paper stage
on the DRAFT pairs, then the PCE passes. Report with the batch's own averages.
