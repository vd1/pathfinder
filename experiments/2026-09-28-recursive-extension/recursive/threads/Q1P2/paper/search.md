# Targeted prior-work search, round 1

Search date: 28 September 2026. The target was a realised-sample certificate
for exact conditional-CVaR obedience with state-independent rewards, a
cycle graph, and an explicit sample and reward bill. Search results below
report what was returned and inspected, not an exhaustive priority claim.

| Query | Return and effect on the paper |
| --- | --- |
| `"conditional CVaR" "obedience" "cycle" certificate sampling rewards` | No result stating the target certificate was returned. The broad result set included Q's survey. |
| `"CVaR" "obedience" "difference constraints" samples` | No matching graph and sampling theorem was returned. |
| `"Finite-Batch CVaR Can Reverse an Obedience-Cycle Test"` | No public copy of supplied P was returned. P is cited as the supplied unpublished manuscript, with a local file URI. |
| `"Learning-Augmented Algorithms: Guarantees, Construction Mechanisms, and System-Level Implications"` | Returned [Q's arXiv abstract](https://arxiv.org/abs/2609.04787). It confirms the survey metadata and scope; the supplied TeX gives the cost and composition details used here. |
| `"CVaR" "incentive compatibility" "samples" "cycle"` | Returned tail-risk best-arm work and broader risk-conscious information design, but no target reward certificate. |
| `"obedience" "CVaR" "confidence" reward` | No exact match to the target was returned. |
| `"sample" "robust obedience" "cycle" rewards` | No exact match to the target was returned. |
| `"CVaR" "best arm identification" confidence intervals 2021` | Returned [Agrawal, Koolen and Juneja](https://proceedings.neurips.cc/paper/2021/hash/d69c7ebb6a253532b266151eac6591af-Abstract.html). Their published tail-risk confidence bounds and fixed-confidence identification make the statistical step prior work. |
| `"incentive compatibility" "confidence intervals" "payments" sample` | Returned sample-based approximate incentive-compatibility work, including [Balcan, Sandholm and Vitercik](https://arxiv.org/abs/1902.09413), but no exact conditional-CVaR reward-cap comparison. |
| `"obedience" "difference constraints" "sampling"` | No paper stating the target combination was returned. |
| `"cycle" "sample complexity" "incentive compatibility"` | Returned other learning and incentive work, without the target cycle certificate. |
| `"risk-conscious Bayesian persuasion" CVaR margin incentive` | Returned [Chen](https://arxiv.org/abs/2605.12094). Section 5.3 of the [full text](https://arxiv.org/html/2605.12094v1) establishes positive-margin stability of strict incentives under risk-value approximation in a different persuasion model. The paper therefore does not claim that margin stability itself is new. |

I also read the abstract pages of
[Prashanth, Jagannathan and Kolla](https://arxiv.org/abs/1901.00997),
[Prashanth and Bhat](https://arxiv.org/abs/1902.10709), and
[Kaufmann, Cappé and Garivier](https://arxiv.org/abs/1407.4443).
The first two establish prior empirical-risk concentration methods, including
CVaR. The last supplies the standard sequential change-of-measure tool used
in the lower-bound discussion. These sources and the NeurIPS proceedings page
were used to verify reference metadata. The arXiv abstract pages also verify
Q, Chen and Balcan. P has no public arXiv or DOI record in the supplied
metadata; its bibliographic details were checked against `inputs/P.tex` and
`inputs/P.json`.

The targeted search did not find the exact local reward-cap comparison, but
it found published versions of its statistical and margin-stability steps.
The contribution is therefore described as the narrow combination in the
stated model, without a priority claim for its ingredients.
