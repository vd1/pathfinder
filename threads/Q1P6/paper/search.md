# Prior-work search record

Searches were run on 12 September 2026. The target was the paper's specific fixed-population ledger repair for potential shaping with changing active coalitions, plus its main Nash-invariance step.

## Queries and results

- arXiv API: `"potential-based reward shaping" AND "multi-agent"`. The API returned no usable matching records in the captured response.
- arXiv API: `"potential-based reward shaping" AND "stochastic games"`. The API returned no paper records.
- arXiv API: `"reward shaping" AND "dynamic agent participation"`. The API returned no paper records.
- arXiv API: `"reward shaping" AND "open multi-agent"`. The API returned no paper records.
- Crossref: `Potential-Based Reward Shaping for Multi-Agent Systems`. This returned the 2011 work of Devlin and Kudenko, a 2014 paper on dynamic agent-based reward shaping, and other broader reward-shaping papers.
- Crossref: `Policy invariance under reward transformations multi-agent`. This returned Lu, Schwartz, and Givigi, “Policy Invariance under Reward Transformations for General-Sum Stochastic Games”, Journal of Artificial Intelligence Research 41 (2011), 397–406, DOI 10.1613/jair.3384.
- Semantic Scholar: `potential-based reward shaping multi-agent systems`. The endpoint returned HTTP 429, so no result from it was used.
- arXiv identifier lookup: `2609.04787,2607.27967`. This verified the titles, author lists, years, and arXiv identifiers of Q and P. The record for P also supplied DOI 10.18653/v1/2026.acl-long.1349.

## What was read and what changed

The full Lu, Schwartz, and Givigi paper was downloaded from the Journal of Artificial Intelligence Research and read. It proves that potential-based shaping preserves Nash equilibria in multi-player general-sum stochastic games. It also states that similar work by Devlin and Kudenko appeared while that paper was under review. Therefore the broad Nash-invariance step and its potential-shaping rationale are treated as published prior work, not as this paper's contribution.

The search did not locate a verified publication stating the narrower construction used here: embed active-coalition softmax credits in a fixed population space, keep inactive coordinates at zero, and retain each population member's shaping ledger on every transition so that entry and exit do not break telescoping. The paper describes this only as the outcome of the recorded search, not as proof of novelty.

Bibliographic metadata for Q and P was checked against the arXiv API abstract records. Metadata for Lu, Schwartz, and Givigi was checked against the DOI/Crossref record and the journal PDF. No unverified search result was added to the bibliography.

## Round 2 search update

The focused search was repeated on 12 September 2026 after revision.

- arXiv API: `"potential-based reward shaping" AND ("changing coalitions" OR "dynamic participation")`. The API reported zero results.
- Crossref: `potential reward shaping changing coalitions`. The leading result was Devlin and Kudenko, ``Dynamic potential-based reward shaping'' (2012), followed by work on POMDPs and other broader shaping settings. The title and metadata were inspected through Crossref. This result concerns a changing potential function, not the paper's fixed-population accounting problem for agents entering and leaving coalitions. It therefore did not change the contribution statement or bibliography. The narrower query produced no evidence that the ledger construction itself had already been published.

The round 2 search therefore left the related-work conclusion unchanged: general policy and Nash invariance under potential shaping is prior work, while the fixed-population ledger construction is presented only as not located by this search, never as a proved novelty claim.
