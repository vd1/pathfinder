# Prior-work search for the Q–P comparator result

Search date: 28 September 2026. Queries below were run as written.
Searches focused on the difference between minimising local CVaRs and
minimising the CVaR of their sum, plus validation at the selected
distributed decision. Search rankings are evidence of discovery, not
evidence of absence.

| Query | What it returned and what I checked |
| --- | --- |
| `"average of local CVaR" "CVaR" "sum" optimization gap` | P and general CVaR optimisation pages; no exact comparator formula in the displayed results. |
| `"sum of CVaRs" "CVaR of the sum" optimizer example` | CVaR aggregation and optimisation examples, including work in stochastic assignment; no displayed result tied to P's finite-time bound. |
| `aggregate CVaR optimization sum individual CVaR minimizers mismatch diversification` | Broad portfolio and optimisation results. |
| `distributed CVaR optimization local risk aggregate risk comparator gap` | P and [Almen and Dentcheva](https://link.springer.com/article/10.1007/s10957-024-02464-9). I read the latter's abstract, risk-measure comparison and numerical section. It explicitly reports different, better decisions when aggregate loss is assessed before risk, so that aggregation insight is prior work. |
| `"10.1016/j.insmatheco.2010.06.001"` | Cheung's *Comonotonic convex upper bound and majorization* in an institutional record. Its DOI landing page was inaccessible to the search tool, so it was not added to the bibliography. |
| `"On Risk Evaluation and Control of Distributed Multi-agent Systems" "CVaR" aggregate individual risks` | The Almen and Dentcheva journal page and its comparison of aggregate and individual-risk evaluation. |
| `"sum of individual CVaR" "CVaR of sum" optimal decision` | Mainly CVaR subadditivity statements; no exact P-specific bound in the displayed results. |
| `"CVaR" "sum of individual" "optimal" dependence distributed` | Risk aggregation and reinsurance work; no exact P-specific bound in the displayed results. |
| `"Modeling Risk for CVaR-Based Decisions in Risk Aggregation"` | [Zinchenko and Asimit](https://openaccess.city.ac.uk/id/eprint/30419/7/jrfm-16-00266.pdf), which studies CVaR under dependence uncertainty. I read its abstract. Its DOI landing page could not be fetched, so it was not added to the bibliography. |
| `"Modeling Risk for CVaR-Based Decisions in Risk Aggregation" arxiv` | The published paper and preprint, with no arXiv abstract page in the displayed results. |
| `"CVaR-Based Decisions in Risk Aggregation" optimizer dependence` | The same dependence-uncertainty paper. |
| `"CVaR" "risk aggregation" "decision" dependence optimization 2023` | The dependence-uncertainty paper and other broad CVaR applications. |
| `"A Distribution Optimization Framework for Confidence Bounds of Risk Measures" arxiv` | [Liang and Luo's arXiv abstract](https://arxiv.org/abs/2306.07059) and [ICML page](https://proceedings.mlr.press/v202/liang23c.html). I read both. Their CVaR confidence-bound work precedes the simple holdout radius used here. |
| `"A Distribution Optimization Framework for Confidence Bounds of Risk Measures" doi` | The same ICML and arXiv records. |
| `"On Risk Evaluation and Control of Distributed Multi-agent Systems" arxiv` | [Almen and Dentcheva's arXiv abstract](https://arxiv.org/abs/2311.10287), used to verify the authors, title and arXiv identifier. The [journal page](https://link.springer.com/article/10.1007/s10957-024-02464-9) verifies the 2024 version of record. |
| `"Modeling Risk for CVaR-Based Decisions in Risk Aggregation" arxiv` | The university record and published PDF, with no arXiv abstract page in the displayed results. |
| `"CVaR" "comparator gap" "local" "aggregate"` | No directly relevant exact formula in the displayed results. |
| `"CVaR" "local" "aggregate" "fallback" validation` | Mostly unrelated applications; no matching local-training, aggregate-audit and fallback theorem in the displayed results. |
| `"CVaR" "joint audit" "local" distributed optimization` | No matching theorem in the displayed results. |
| `"sum of local CVaRs" "aggregate CVaR"` | No matching theorem in the displayed results. |

The review changed the claim of contribution: aggregation order affecting
optimal decisions is already published by Almen and Dentcheva, and CVaR
confidence bounds are already studied by Liang and Luo. The paper therefore
attributes those steps and claims only the ledger's specific comparator
accounting and conditional interface analysis for Q and P. I verified Q
against its [arXiv abstract](https://arxiv.org/abs/2609.04787) and P
against [its abstract](https://arxiv.org/abs/2609.04460). All bibliography
entries were checked against an arXiv abstract page or the journal DOI
landing page.
