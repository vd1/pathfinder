# Related-work search record

Searches were run on 12 September 2026. The aim was to find the specific uniform expected empirical-smoothed CVaR bound and its optimiser consequences, rather than general work on CVaR or distributed optimisation.

The two exact-result arXiv queries and the metadata query were rerun during
round 2. Their results were unchanged.

## Queries and results

- arXiv API: `"empirical CVaR" AND "DKW"`. Returned no records.
- Crossref: `uniform empirical CVaR bound DKW`. Returned broad matches. The relevant match was *Statistical Model Checking Beyond Means: Quantiles, CVaR, and the DKW Inequality* (2025). Its title concerns DKW-based CVaR bounds, but it does not match the paper's optimisation-surrogate setting. It was not added to the bibliography because it was not needed for a claim in the paper.
- arXiv API: `"CVaR" AND "Wasserstein" AND "empirical"`. Returned eleven records. The directly relevant item was Prashanth L. A. and Sanjay P. Bhat, *A Wasserstein distance approach for concentration of empirical risk estimates*, arXiv:1902.10709.
- arXiv API: `"CVaR" AND "objective perturbation"`. Returned no records.
- arXiv API: `"empirical-smoothed" AND "CVaR"`. Returned no records.
- arXiv API, round 2: `all:"empirical-smoothed" AND all:CVaR`. Returned zero records.
- arXiv API, round 2: `all:"objective perturbation" AND all:CVaR`. Returned zero records.

## What was read and what changed

The abstract page and full PDF of arXiv:1902.10709 were read. The paper treats empirical CVaR as an optimised-certainty-equivalent risk measure, proves Wasserstein continuity, derives concentration bounds, and discusses earlier empirical-CVaR concentration results. This establishes that the concentration route used in the present proof is prior work.

Accordingly, the paper does not claim a new empirical-CVaR concentration theorem. It presents the contribution as a specific synthesis: apply the published stability route to P's pointwise expected empirical-smoothed surrogate, add P's smoothing term, and derive the static optimiser, allocation, and conditional individual-rationality consequences recorded in the ledger. No search result stated that full combination.

## Metadata verification

Titles, authors, years, and identifiers for Q (arXiv:2608.29130), P (arXiv:2609.04460), and Prashanth and Bhat (arXiv:1902.10709) were checked against their arXiv abstract metadata. Every bibliography entry contains its arXiv identifier and abstract-page URL.
