# Related-work search for the Q1P6 result

Search date: 27 September 2026. The target was the accounting of comparison-derived softmax potentials
under full pooling and active-agent entry, plus whether comparison accuracy controls a downstream
training outcome. Searches were read against the linked primary papers before inclusion in the manuscript.

| Query | What it returned and effect on the paper |
| --- | --- |
| `"MARS-RA" "potential" "pooling" reward shaping ranking` | No checked paper deriving P's full-pooling or entry-mask fork. Kept the fork conditional and specific to P's equations. |
| `"multi-agent" "potential-based reward shaping" "entry" "exit" active agents` | General multi-agent shaping work, including Difference Advantage Estimation, but no checked match to P's reentry mask. Kept implementation status unresolved. |
| `"potential based reward shaping" "agent reentry" mask telescoping` | General potential-shaping and policy-gradient papers, with no checked match for the displayed reentry identity. |
| `"potential-based reward shaping" "policy gradient" variance Gupta` | Found Gupta et al., *Behavior Alignment via Reward Function Optimization* (2023), which explicitly shows unchanged expected updates and possible increased variance. Removed any novelty claim for the variance diagnostic. |
| `site:arxiv.org/abs/2609.04787` | The search engine did not return a useful result. Direct opening of the arXiv abstract verified Q's title, authors, year and identifier. |
| `site:arxiv.org/abs/2607.27967` | The search engine did not return a useful result. Direct opening of the arXiv abstract verified P's title, authors, year and identifier. |
| `Dynamic Potential-Based Reward Shaping Devlin Kudenko DOI 2012` | Found the official AAMAS 2012 paper. Its text proves dynamic potential-shaping invariance, so the manuscript calls cancellation prior theory. The DOI landing page could not be verified, so it was not added to the bibliography. |
| `Behavior Alignment via Reward Function Optimization Gupta arxiv 2023` | Found arXiv:2310.19007; its abstract verified title, authors and year. Read the NeurIPS paper's potential-shaping result. |
| `"Dynamic potential-based reward shaping" "10.5555/2343576.2343638" site:dl.acm.org` | Did not produce an accessible DOI landing page. No bibliography entry was made. |
| `"Dynamic potential-based reward shaping" site:doi.org` | No usable DOI landing page for the cited dynamic-shaping paper. |
| `site:arxiv.org "Difference Advantage Estimation for Multi-Agent Policy Gradients"` | No usable arXiv abstract result; the official PMLR paper was read. It studies multi-agent potential-based difference rewards and advantage estimation, so the draft does not claim general novelty for multi-agent shaping. It was not added to the bibliography. |
| `"Dynamic Potential-Based Reward Shaping" "arXiv" Devlin Kudenko` | No arXiv abstract for the 2012 paper; surfaced related vision-language shaping work. |
| `"Dynamic potential-based reward shaping" "doi.org/10.5555"` | No usable DOI landing page. |

A related result surfaced while following the dynamic-shaping search: Müller and Kudenko,
*Automating Potential-based Reward Shaping with Vision Language Model Guidance*, arXiv:2606.27180
(2026). Its abstract and full HTML paper were read. It already uses vision-language pairwise
preferences to construct a shaping potential and studies label quality and learning speed in
single-agent environments. The paper now states plainly that this main step predates the present
Q--P analysis. Its arXiv abstract verified its title, authors, year and identifier.

The narrow searches did not establish that no prior work contains the exact pooling or reentry
equations. The paper therefore claims a conditional analysis of P, not priority over the literature.
