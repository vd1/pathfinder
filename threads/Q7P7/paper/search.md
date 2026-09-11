# Related-work search record

Searches were run on 12 September 2026. OpenAlex and Crossref were used for discovery. Candidate metadata was checked against an arXiv abstract record or DOI metadata before citation.

## Queries and results

1. OpenAlex full-text query: `"voluntary workload migration" mechanism carbon intensity forecast error`

   Returned *ElectricityEmissions.jl: A Framework for the Comparison of Carbon Intensity Signals* as the only relevant result near the top. Its abstract studies how carbon-intensity signal choice affects load-shifting assessments. It does not present strategic payments or the certificate in the paper.

2. OpenAlex full-text query: `"nodal carbon intensity" workload migration forecast`

   Returned carbon-aware data-centre scheduling and workload-forecasting papers, including *Carbon-Aware Computing for Datacenters*. That paper uses next-day carbon-intensity forecasts and risk-aware optimisation for flexible workloads. It establishes that forecast-conditioned shifting is prior work, so the paper does not claim that setting as new.

3. OpenAlex full-text query: `carbon aware workload scheduling forecast error robustness`

   Returned carbon-aware scheduling, robust scheduling, and workload-prediction papers. The most relevant established works were *Carbon-Aware Computing for Datacenters*, *Let's wait awhile*, and later carbon-aware schedulers. No returned record joined the Garjani mechanism to baseline-relative voluntary migration.

4. Crossref bibliographic query: `carbon aware workload scheduling forecast error`

   Returned *Forecast-to-Realized Carbon-Aware Dispatch Evaluation for AI Data Centers with Constrained Workload Migration and Battery Storage* among the most specific results. Its DOI abstract was read. It evaluates constrained geographic migration under forecast error and reports realised carbon, cost, peak, service, and regret outcomes. This changed the contribution statement: forecast-to-realised workload-dispatch evaluation is not claimed as new. The present paper claims only the strategic specialisation and explicit directional sufficient condition.

5. OpenAlex full-text query: `"carbon-aware" "forecast error" data center scheduling`

   Returned *Carbon-Aware Computing for Datacenters*, *Exploring the Impacts of Power Grid Signals on Data Center Operations using a Receding-Horizon Scheduling Model*, *On the Limitations of Carbon-Aware Temporal and Spatial Workload Shifting in the Cloud*, and the 2026 forecast-to-realised preprint. Their abstracts were read. They establish forecast-based scheduling, signal sensitivity, and practical limitations, but the records inspected did not state the quadratic-payment construction or the schedule-specific dual-norm margin certificate.

## Verification

The titles, author lists, years, and arXiv identifiers for Q, P, and the three cited arXiv papers were checked through the arXiv API records for 2608.29130, 2607.26560, 2106.11750, 2204.06654, and 2306.06502. The metadata for DOI 10.1145/3679240.3734597 and DOI 10.2139/ssrn.7232709 was checked through the Crossref DOI records. Every item retained in `references.bib` has a verified URL and is cited in `paper.tex`.

## Round 3 search check

The following focused queries were rerun on 12 September 2026 after the second review.

6. OpenAlex full-text query: `voluntary workload migration mechanism carbon intensity forecast error`

   The leading results were a review of high-performance-computing decarbonisation and a survey of workload shifting. Neither result stated the combination of voluntary baseline-relative flows, strategic quadratic payments, and a directional forecast-error certificate.

7. OpenAlex full-text query: `schedule-specific forecast error carbon-aware workload migration strategic mechanism`

   The leading relevant result was a review of carbon-aware spatial and temporal workload shifting. The remaining leading records concerned general climate or cloud scheduling topics. No result inspected stated the paper's combined result.

8. Crossref bibliographic query: `carbon aware workload migration forecast error mechanism`

   This again returned *Forecast-to-Realized Carbon-Aware Dispatch Evaluation for AI Data Centers with Constrained Workload Migration and Battery Storage* as the closest result. Its DOI abstract describes forecast-to-realised evaluation with constrained migration, battery storage, and regret. It does not describe strategic quadratic payments or the stated dual-norm margin test. The search therefore left the related-work conclusion unchanged: forecast-to-realised evaluation is established prior work, while no inspected source published the specific combined result.
