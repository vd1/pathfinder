# Targeted prior-work search, round 1

Searches were run on 25 September 2026. The focus was the completed fixed-price comparator
and the small-price-error rationing example. Search results were read against abstracts or
available manuscripts before citation.

| Query | Return and effect on the paper |
| --- | --- |
| `"Learning-Augmented Algorithms: Guarantees, Construction Mechanisms, and System-Level Implications"` | Found [Q's arXiv abstract](https://arxiv.org/abs/2609.04787), used to verify its title, seven authors and 2026 date. |
| `"The Cost of Price Discovery in an LLM Double Auction"` | The recorded search found no arXiv or DOI record for P. Its title, campaign author and date come from `inputs/P.tex` and `inputs/P.json`. It is now included verbatim as Supplementary File S1. |
| `"The cost of price discovery in an LLM double auction" Pathfinder` | Returned no external record for the supplied local P manuscript in this search. |
| `double auction fixed price optimal welfare rationing arbitrarily small price error welfare loss` | Returned broad auction and welfare papers, including the Santa Fe trading-automata study and work on clock auctions. No exact fixed-schedule rationing example was located. |
| `learning augmented double auction price predictions welfare rationing` | Returned learning-augmented auction papers, including single-item revenue auctions and clock auctions, not this double-auction price-response construction. |
| `"price prediction" "double auction" "welfare" rationing` | No direct match for the claimed construction. |
| `"posted price" prediction error discontinuous welfare rationing` | No direct match for the claimed construction. |
| `"double auction" "fixed price" "prediction" welfare` | Returned adjacent fixed-price and prediction-market results; no paper combining this instance, paid advice and its execution path. |
| `"costly predictions" "double auction"` | No direct result for paid prediction queries in this double auction. |
| `"Behavior of Trading Automata in a Computerized Double Auction Market" DOI` | Found the [Santa Fe working paper](https://www.santafe.edu/research/results/working-papers/behavior-of-trading-automata-in-a-computerized-dou). It reports strong performance by a simple trading rule but neither the exact fixed schedule nor a paid-advice result. It was not added to the bibliography because no arXiv abstract or DOI landing page was verified. |
| `"fixed price" "double auction" "gain from trade" arxiv` | Found [Colini-Baldeschi et al.](https://arxiv.org/abs/1710.08394). Its published fixed-price double-auction analysis establishes that the main fixed-price idea is prior work. The paper now states this plainly and limits its claim to an instance-specific calculation and negative control. |
| `"price prediction" "double auction" "costly" LLM` | No direct match for optional costly LLM price advice in this fixed-value double auction. |

The relevant arXiv abstract pages were opened and read:
[Q](https://arxiv.org/abs/2609.04787),
[Struski et al.](https://arxiv.org/abs/2609.02580),
[Colini-Baldeschi et al.](https://arxiv.org/abs/1710.08394) and
[Gkatzelis et al.](https://arxiv.org/abs/2408.06483).
The [fixed-price full text](https://arxiv.org/pdf/1710.08394) was also checked for its
treatment of eligibility and rationing.
These searches do not support an exhaustive novelty claim.

## Round 2 checks

The following queries were run on 25 September 2026. The search results were checked against the relevant arXiv abstract pages and the supplied manuscript.

| Query | Return and effect on the paper |
| --- | --- |
| `"The Cost of Price Discovery in an LLM Double Auction" site:arxiv.org` | No matching arXiv abstract appeared in the returned results. This supports only the wording that the recorded search found no arXiv record. |
| `"The Cost of Price Discovery in an LLM Double Auction" site:doi.org` | No matching DOI landing page appeared in the returned results. This supports only the wording that the recorded search found no DOI record. |
| `"The Cost of Price Discovery in an LLM Double Auction"` | Returned no matching publication record in this search. P is therefore supplied as Supplementary File S1 rather than assigned an invented public identifier. |
| `"double auction" "small price error" rationing welfare` | Returned adjacent price-discovery material but no direct match to the fixed-schedule rationing construction. The paper retains the limited, model-specific claim. |

Supplementary File S1 is `S1-P.tex` beside `paper.tex` in the review bundle. It is byte-for-byte identical to `inputs/P.tex`; its SHA-256 digest is `748c7b742fe02eea44baa4d71a37e09089c2d68e01cc5782b0549e5fa608e0c7`. The bibliography cites the stable supplementary-file identifier S1 and links to the included file. P's author and date metadata can only be checked against the supplied `inputs/P.json`, because this search found no arXiv abstract or DOI landing page for it. No external bibliographic claim is made for P.

The title, authors and year of Q, Struski et al., Colini-Baldeschi et al. and Gkatzelis et al. were rechecked against their arXiv abstract pages: [Q](https://arxiv.org/abs/2609.04787), [Struski et al.](https://arxiv.org/abs/2609.02580), [Colini-Baldeschi et al.](https://arxiv.org/abs/1710.08394) and [Gkatzelis et al.](https://arxiv.org/abs/2408.06483). The fixed-price mechanism remains acknowledged as prior work; no contribution claim was expanded.
