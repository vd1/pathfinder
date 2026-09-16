# Q7P1 literature search, round 1

Search date: 13 September 2026. The scope was the payment correction, expected empirical CVaR objective, economic
perturbation bounds and nested monotone learner. The search does not establish absence of matching prior work.
Queries below were run through web search; some were repeated individually after an initial batch. Results listed
are the relevant or representative returns, not an exhaustive export of irrelevant hits.

## Queries and returns

1. `"CVaR" "mechanism" "budget balance" rebate`

   Returned energy trading and benefit-allocation work, including [A Self-Governed Online Energy Management and
   Trading For Smart Micro/Nano-Grids](https://irep.ntu.ac.uk/id/eprint/37938/1/1198465_Sanei.pdf), [inter-area
   reserve benefit allocation](https://doi.org/10.1016/j.omega.2022.102711), and wind-farm aggregation patents. The
   energy-trading PDF was opened and its formulation screened. These returns did not identify the correction to Q's
   printed payment. The reserve-allocation result discusses coalitional allocation; it was screened from the
   returned publisher text, not used as a theorem source. No bibliography entries were added from this query.

2. `"CVaR" "surrogate" "approximate Nash" smoothing`

   Returned WSC 2022 proceedings, including retrospective approximation with importance sampling for CVaR, and UAI
   2021 proceedings including tail-estimator bias correction. It did not produce a direct match for the economic
   oscillation bound. The closest game-smoothing comparison instead came from the ledger's Cui--Shanbhag lead, read
   below. Proceedings-list hits were screened for relevance, not treated as verified full-paper evidence.

3. `"Risk-Averse No-Regret Learning in Online Convex Games" arxiv`

   Returned [arXiv:2203.08957](https://arxiv.org/abs/2203.08957), the ICML paper and mirrors. Read the [PMLR full
   paper](https://proceedings.mlr.press/v162/wang22w/wang22w.pdf), particularly Algorithm 1, Lemmas 2--3 and the
   distribution-function comparison in Appendix A.2. The empirical CVaR one-point estimator and its principal
   estimation step are already published. The paper therefore disclaims novelty for this estimator.

4. `"Sample average approximation of conditional value-at-risk based variational inequalities" arxiv`

   Returned [arXiv:2208.11403](https://arxiv.org/abs/2208.11403) and the [journal landing
   page](https://doi.org/10.1007/s11590-023-01996-9). Read the [full preprint](https://arxiv.org/pdf/2208.11403),
   including the VI definition, Section 3 and Theorem 3 with its proof. Its target is a random SAA operator and
   solution-set approximation. This differs from the deterministic expected empirical objective implemented here.
   The distinction is stated in related work.

5. `"quadratic" "mechanism" "opponent" "individual rationality"`

   Returned general mechanism-design documents, researcher listings, a duopoly adjustment paper and
   quadratic-voting material. No directly matching correction was identified. These broad hits were not used to
   support priority or mathematical claims.

6. `"CVaR" "expected empirical" bias optimisation`

   Returned [A revised approach for risk-averse multi-armed bandits under CVaR
   criterion](https://www.sciencedirect.com/science/article/abs/pii/S0167637721000675), task-sampling papers and
   empirical-risk material. The bandit publisher page failed to open; only its returned description of an expected
   empirical CVaR target was available. It is not cited and no conclusion about its proofs is drawn. This query did
   not establish novelty of expected empirical risk as an objective.

7. `"risk" "quadratic mechanism" rebate`

   Returned quadratic-voting/funding material, forecasting competitions and power-market risk hedging. No directly
   matching resource-allocation rebate was identified. These results were screened by title and returned text, and
   were not used as technical sources.

8. `"CVaR" "oscillation" equilibrium`

   Returned mostly false positives involving variable capacitors, oscillators and other meanings of CVAR, plus
   unrelated energy applications. This query was uninformative about the result. It supplies no evidence for
   priority.

## Direct follow-up of ledger sources

- [Cui and Shanbhag, arXiv:2104.07860](https://arxiv.org/abs/2104.07860): read [full text, Section
  3.2](https://arxiv.org/html/2104.07860v2), including Propositions 5--6 and their surrounding recurrence and
  convergence arguments. Stochastic approximation of resolvents with polynomial inner effort exceeding degree two
  already appears there. The learner is presented as an application with explicit assumptions, not a new proximal
  method.
- [Wang et al., arXiv:2403.10399](https://arxiv.org/abs/2403.10399): read [full text, Sections III--IV and the
  theorem proof](https://arxiv.org/html/2403.10399v1). Algorithm 1 uses loss gradients and estimated quantiles;
  Theorem 1 gives a time-averaged squared-distance guarantee under strong monotonicity. The paper uses this precise
  comparison rather than a generic last-iterate convergence attribution.
- Q and P: verified their abstract pages and read the supplied TeX at the payment, matrix conditions, surrogate
  definition, smoothing identity and integrated DKW calculation. Mathematical claims about these sources are
  anchored to ledger entries in comments throughout paper.tex.

## Bibliographic verification

All entries were checked before inclusion. All entries have URL fields and are cited; arXiv identifiers are
included. The note fields also print links because the required plain BibTeX style does not normally print URL
fields.

| Key | Verification page | Verified title, authors and year |
| --- | --- | --- |
| Q | [arXiv:2608.29130](https://arxiv.org/abs/2608.29130) | A Systematic Approach to Mechanism Design with Stochastic Dynamic Stability; Shaya Garjani, Mohammad Shokri, Hamed Kebriaei; 2026 |
| P | [arXiv:2609.04460](https://arxiv.org/abs/2609.04460) | Distributed risk-averse optimization via CVaR; Siyi Wang, Kun Huang, Lei Xu, Karl H. Johansson; 2026 |
| wang2022 | [arXiv:2203.08957](https://arxiv.org/abs/2203.08957) | Risk-Averse No-Regret Learning in Online Convex Games; Zifan Wang, Yi Shen, Michael M. Zavlanos; 2022. ICML publication also checked at [PMLR](https://proceedings.mlr.press/v162/wang22w.html). |
| cui2021 | [arXiv:2104.07860](https://arxiv.org/abs/2104.07860) | On the computation of equilibria in monotone and potential stochastic hierarchical games; Shisheng Cui, Uday V. Shanbhag; first submitted 2021, version read revised 2022 |
| wang2024 | [arXiv:2403.10399](https://arxiv.org/abs/2403.10399) | Learning of Nash Equilibria in Risk-Averse Games; Zifan Wang, Yi Shen, Michael M. Zavlanos, Karl H. Johansson; 2024 |
| cherukuri | [DOI landing page](https://doi.org/10.1007/s11590-023-01996-9) | Sample average approximation of conditional value-at-risk based variational inequalities; Ashish Cherukuri; journal volume 18, pages 471-496, 2024, online publication 2023. Preprint identifier 2208.11403 checked separately. |

## Effect on the contribution

The manuscript claims a specific correction and conditional combination. Existing work already supplies the CVaR
estimator and generic nested proximal learning step. The payment repair and error-oscillation economic package were
not identified in the sources examined, but the search is bounded and several broad queries were weak. No claim of
comprehensive novelty or absence of prior work is made. No new mathematical result was added from the search.
