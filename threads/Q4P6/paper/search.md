# Related-work search record

Searches were run on 12 September 2026. Metadata for every cited arXiv item was checked against its arXiv abstract/API record. Candidate papers were read from their PDFs before the related-work section was written.

For round 3, the exact-title and identifier checks below were rerun, and the focused searches were reviewed specifically for whether a single jointly labelled item could support the moment argument.  It cannot: the cited single-coin work and the present theorem use population correlations estimated from repeated shared assignments.  This changed the sampling-design statement, proof wording, limitations, and empirical-test paragraph, but did not add a reference or enlarge the contribution.

## Queries and results

### `"pairwise comparison" AND "worker reliability"` on arXiv

Returned two directly relevant papers:

- Shejole et al., *Finding the Signal in the Spam: Jointly Learning Rewards and Worker Reliability from Pairwise Comparisons*, arXiv:2608.10045. It learns rewards and worker competency jointly in a Boltzmann-rational Bradley--Terry extension using an expectation-maximisation method.
- Nordio, Tarable, and Leonardi, *Ranking a Set of Objects using Heterogeneous Workers: QUITE an Easy Problem*, arXiv:2310.02016. It jointly estimates worker reliability and object quality from repeated pairwise comparisons.

Change to the paper: these results prevent any claim that joint ranking and heterogeneous-reliability estimation is new. Both are discussed and cited.

### `"rank-one" AND crowdsourcing` on arXiv

Returned work including Ma et al., *Gradient Descent for Sparse Rank-One Matrix Completion for Crowd-Sourced Aggregation of Sparsely Interacting Workers*, arXiv:1904.11608, and its precursor *Crowdsourcing with Sparsely Interacting Workers*, arXiv:1706.06660. Their single-coin model uses pairwise worker-label correlations to form a rank-one skill matrix and gives graph conditions for label-free identifiability.

Change to the paper: this search found that the main agreement-moment step in the note is already published. The theorem and abstract now say so plainly. The claimed contribution is reduced to a conditional interface that combines known calibration with Bradley--Terry edge inversion and identifies the unresolved incentive bootstrap.

### `heterogeneous workers pairwise ranking reliability` within the retrieved papers and their related-work sections

This reading confirmed that QUITE uses repeated assignment of the same pair to unequal workers and estimates qualities and reliabilities jointly. The 2026 paper compares several heterogeneous Bradley--Terry-style baselines and develops another joint model.

Change to the paper: the related-work section distinguishes these joint response models from the note's shared-realisation agreement factorisation. The paper does not claim a new joint estimator.

### Exact-title and arXiv-ID lookups for Q and P

Lookups for arXiv:2609.01595 and arXiv:2607.27967 verified the titles, complete author lists, and years of Q and P.

Change to the paper: Q and P receive verified BibTeX entries and are cited by name in the introduction.
