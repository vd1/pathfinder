# Source audit for the recursive extension seeds

Checked 28 September 2026. Scope: the two selected completed seed papers and
their cited scientific dependencies, not every bibliography in all campaigns.
Public metadata checks are distinct from mathematical validation and do not
establish literature novelty. Immediate local sources remain unpublished.

## Public sources

- Zhao and colleagues, *Learning-Augmented Algorithms: Guarantees,
  Construction Mechanisms, and System-Level Implications*: title and authors
  match [arXiv 2609.04787](https://arxiv.org/abs/2609.04787).
  [Version 1, sections 1 and 3](https://arxiv.org/html/2609.04787v1)
  distinguish prediction errors and guarantees from system-level assumptions.
  The ranking seed does not inherit a downstream performance theorem merely
  by providing a prediction object.
- Bergemann, Koh and Morris, *Mechanism Design for Alignment and Control*:
  title, authors and date match [arXiv 2609.01595](https://arxiv.org/abs/2609.01595).
  [Version 1, section 2.4, Lemma 1 and Proposition 2](https://arxiv.org/html/2609.01595v1)
  confirm the signal-cycle condition for supporting state-independent rewards
  and the additional report-stage condition. The risk seed deliberately uses
  the former in a one-type conditional-utility embedding, not the full mechanism.
- Ma, Olshevsky, Saligrama and Szepesvari, *Crowdsourcing with Sparsely
  Interacting Workers*: metadata and the sparse single-coin identification
  antecedent match [arXiv 1706.06660](https://arxiv.org/abs/1706.06660).
  This checks the attribution, not a new reproduction of that paper's proofs.
- Wu, Niezink and Junker, *A Diagnostic Framework for the Bradley--Terry Model*:
  the [publisher article](https://academic.oup.com/jrsssa/article/185/Supplement_2/S461/7069516)
  confirms 2022, volume 185, Supplement 2, S461--S484 and DOI
  10.1111/rssa.12959. Its introduction and abstract concern model diagnostics,
  not certification that observed agreement identifies an intended target.
  Direct DOI retrieval failed; the publisher article route succeeded.
- Ieong, So and Sundararajan, *Stochastic Mechanism Design*: the
  [publisher record](https://link.springer.com/chapter/10.1007/978-3-540-77105-0_26)
  confirms authors, WINE 2007 and pages 269--280. The
  [author-hosted paper](https://www.se.cuhk.edu.hk/~manchoso/papers/smd-wine07.pdf)
  explicitly assumes risk neutrality at the first stage and discusses
  sampling-based approximate incentives. It is an antecedent, not a proof
  of the seed's conditional-CVaR construction.
- Miller and Yang, *Optimal Control of Conditional Value-at-Risk in Continuous
  Time*: [arXiv 1512.05015](https://arxiv.org/abs/1512.05015) confirms the original
  2015 submission and identifies time inconsistency as an existing issue.
  The later journal record is 2017; citing the 2015 preprint is consistent.

## Local-source custody and corrections

R1's P is the original Q4P6 accepted manuscript, supplied to the first pilot
as S1. R2's P is the September 23 Q7P1 accepted manuscript, supplied as S4.
The preparation script preserves these immediate sources as package files,
records SHA-256 identities, and replaces relative URL fields with explicit
unpublished-manuscript locators. No public identifier is invented.

The final archived reviews requested those bibliography corrections. R1's
review also requested the explicit range 0 < tau <= 1/2 and joint labels of
the same realised draw for overlap populations. The versioned seed applies
these requests. R2 additionally replaces wording about a chosen reward with
existence of a common reward, matching its actual theorem.

The original S1 prose overstates that correlated errors destroy factorisation.
R1 already identifies and corrects that statement; its clean-model theorem is
not refuted. Do not alter the archival S1 to hide the ancestry of this correction.

## What is and is not cleared

The selected references exist and the checked attribution boundaries are
consistent with the seed arguments. The old automatic HTTP 406 warnings are
not evidence that these papers are missing. They remain part of the historical
build record and are not deleted. The focused mathematical checks are in
`notes/check_recursive_claims.py`; no external referee has certified the edits,
and this audit is not an exhaustive prior-art search.
