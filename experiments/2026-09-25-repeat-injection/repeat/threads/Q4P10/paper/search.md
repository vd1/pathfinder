# Prior-work search for Q4P10, round 1

Search date: 25 September 2026. Queries below are recorded verbatim. Results listed are the relevant returns, or the reason a return was excluded. Searches targeted the priority-prize equilibrium step and the auxiliary bounded-score calculation.

| Query | Return and disposition |
| --- | --- |
| `budget balanced priority winner reward coverage game social optimum Nash equilibrium stochastic success` | Returned cost-sharing characterisations, especially Gopalakrishnan, Marden and Wierman (2014), and unrelated facility-location work. Led to ordered protocols. |
| `priority based cost sharing facility location welfare optimum Nash equilibrium submodular coverage rewards` | Returned the same cost-sharing characterisation and facility-location papers. No exact stochastic job-prize model. |
| `ranking priority highest successful agent prize allocation efficient assignment Nash equilibrium` | Returned prize contests and resource-allocation material, without the target-first job-prize theorem. |
| `resource allocation game job prize highest priority successful agent social optimum Nash equilibrium` | Returned broad resource-allocation and scheduling papers, without the specific result. |
| `"priority" "welfare maximizing" "Nash equilibrium" coverage game` | Returned priority scheduling and other broad optimisation examples. No exact prize-splitting result. |
| `"priority" "social optimum" "Nash equilibrium" welfare sharing games` | Returned priority scheduling and tax mechanisms, without the target-first proof. |
| `"priority-based" "marginal contribution" "budget balance" game` | Returned material on priority-based welfare distribution, prompting the Marden and Wierman search. |
| `"ordered" "marginal contribution" "budget balanced" "Nash"` | Returned ordered-protocol and marginal-contribution literature. |
| `"ordered protocols" "social optimum" "Nash"` | Returned earlier network cost-sharing protocols, with equilibrium existence but no match to the job-prize application. |
| `"ordered protocols" "price of stability" cost sharing` | Returned Marden and Wierman's work on priority-based distribution and optimal equilibria. This was the decisive lead. |
| `"priority" "coverage games" "price of stability" welfare` | Returned Marden and Wierman's priority-based result and related coverage literature. |
| `"priority-based" "welfare" "price of stability" distribution rule` | Returned the priority-based distribution result and its optimal-equilibrium proof. |
| `Marden Wierman Overcoming the limitations of utility design for multiagent systems DOI 2013` | Identified the 2013 journal article and DOI `10.1109/TAC.2013.2237831`. |
| `Overcoming Limitations of Game-Theoretic Distributed Control Jason Marden Adam Wierman DOI` | Found the authors' earlier conference paper; its full text has a priority-based welfare rule and an optimal-equilibrium argument. |
| `site:ieeexplore.ieee.org/document/6403513 "Overcoming" "Marden"` | IEEE page did not expose readable bibliographic text to the search tool. DOI metadata was obtained directly instead. |
| `site:doi.org/10.1109/TAC.2013.2237831 Marden Wierman` | No useful indexed landing-page return. DOI content negotiation supplied verified metadata. |
| `site:arxiv.org "Overcoming the Limitations of Utility Design for Multiagent Systems"` | No arXiv version found. |
| `"Overcoming the Limitations of Utility Design for Multiagent Systems" pdf Marden Wierman ordered protocols lemma` | Found the text of Lemma 4.1: rank optimal-profile incumbents ahead of other agents on each resource, then the optimum is an equilibrium. The same construction is the main step in the Q4P10 note. |
| `"Overcoming the Limitations of Utility Design for Multiagent Systems" "Lemma" "ordered"` | Confirmed the same Lemma 4.1 and its proof, including the marginal-contribution comparison. |
| `bounded proper scoring rule total variation lower bound incentive gap B >= M/TV peer prediction` | Returned general scoring-rule material, without this exact two-type payment inequality. |
| `peer prediction bounded payments total variation indistinguishable types incentive lower bound` | Returned peer-prediction papers and general budget constraints, without the exact bound in the note. |
| `"total variation" "peer prediction" "payments" lower bound` | Returned general peer-prediction literature, without an exact match. The paper treats the bound as a narrow elementary consequence of its stated assumptions, not as a broad novelty claim. |

## Sources read and verified

- [Bergemann, Koh and Morris, arXiv:2609.01595](https://arxiv.org/abs/2609.01595): abstract page checked for title, authors, year and identifier; the supplied Q source was read for its reward and peer-discipline assumptions.
- [Hansen, Torrielli, Tonini and Poech, arXiv:2607.14865](https://arxiv.org/abs/2607.14865): abstract page checked for title, authors, year and identifier; the supplied P source was read for split prizes, discussion costs and deactivation.
- [Marden and Wierman, 2013](https://doi.org/10.1109/TAC.2013.2237831): DOI metadata checked for title, authors, year, journal and pages. [Full text of Lemma 4.1](https://www.researchgate.net/publication/228755678_Overcoming_the_Limitations_of_Utility_Design_for_Multiagent_Systems) was read. It already establishes the target-first ordered-protocol equilibrium step for submodular distributed-welfare games. This changes the contribution from a general new theorem to a specialisation and boundary analysis for Q and P.
- [Gopalakrishnan, Marden and Wierman, arXiv:1402.3610](https://arxiv.org/abs/1402.3610): abstract and relevant sections on ordered and marginal-contribution welfare sharing were read. It corroborates the established protocol family but is not cited in the short paper because the earlier exact lemma is the closer antecedent.
