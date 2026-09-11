# Related-work search record

Search date: 11 September 2026.

The search targeted the paper's specific result: a split-conformal upper bound on room-level Hausdorff wall-set error transferred through the distance-to-set inequality to simultaneous correctness of non-abstained decisions at a hard wall-distance gate.

## Queries and returns

1. arXiv API query: `all:"Hausdorff distance" AND all:"conformal"`

   Return: no results could be retrieved. The request to `https://export.arxiv.org/api/query` failed because the sandbox could not resolve the host.

2. Local full-text query across Q and P: `conformal|hausdorff|set distance|distance-to-set|abstain|selective`

   Return: Q discusses split conformal under exchangeability and warns that marginal coverage does not automatically bound downstream cost. P contains the wall-distance gate but no conformal calibration or Hausdorff coverage result. No occurrence in either paper states the combined coverage-to-gate reduction.

3. Local peer-record query across `ledger.jsonl`, `ada/`, and `emmy/` for the same terms and for `first gate`, `union bound`, and `dependency region`.

   Return: the peer derivations establish the combined result and independently cross-check it. They also identify its scope: simultaneous first-gate agreement without a pointwise union bound, marginal rather than conditional coverage, and regional rather than pointwise fallback.

4. Metadata check for Q and P against `inputs/Q.json`, `inputs/P.json`, and the title and author blocks in `inputs/Q.tex` and `inputs/P.tex`.

   Return: titles, author lists, dates, and arXiv identifiers agree within the supplied records. Live arXiv abstract pages could not be reached from the sandbox.

## Effect on the paper

No additional bibliographic entry was added because no external candidate could be checked against an arXiv abstract page or DOI landing page. The related-work section therefore makes no literature-wide priority claim. It states only that the reduction is not present in Q or P and records incomplete external novelty verification as a limitation and open task.
