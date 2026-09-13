# Q4P6 targeted reassessment

## Findings, ordered by severity

**Verdict: SURVIVES; RETAIN_DRAFT; publication readiness NOT_ESTABLISHED. No fatal mathematical defect was
found in the stated population interface theorem.** Its assumptions imply its identification conclusion.
Retain the conditional draft, with the local exposition corrections below. These corrections do not require
changing the theorem or replacing the candidate.

1. **Medium: the attribution of convergence to P needs qualification.** `inputs/r.tex:49` says P proves
   convergence under a common Bradley-Terry vector and a connected comparison graph. This accurately reflects
   P's stated claim (`inputs/P.tex:361-376`), but exceeds what those conditions alone establish. P's appendix
   additionally invokes uniform pair sampling (`inputs/P.tex:698-704`); its argument converts an approximate
   Taylor expansion into an equality without controlling a remainder (`inputs/P.tex:707-725`). Logistic
   curvature also depends on score differences, not just graph topology. A finite unregularized MLE need not
   exist on a connected undirected comparison graph. Revise the attribution to distinguish P's claimed
   statistical convergence, with sampling and regularity qualifications, from the elementary population
   identification used by r. This is a source-assessment correction, not a broken step in r's proof
   (`inputs/r.tex:100-109`), which uses known population probabilities and no MLE or rate.

2. **Medium for publication, not correctness: publication-level novelty is not established.** The contribution
   statements in `inputs/r.tex:24,37,112-114,128-130` correctly disclaim a new calibration method. The
   inspected primary sources already contain the moment factorisation and related heterogeneous ranking
   methods. Combining this calibration with logistic inversion supports a useful explanation of the Q/P
   interface, but the draft supplies no demonstrated new identification technique, strategic implementation
   theorem, or statistical guarantee. This limits the publication judgment independently of the theorem's
   validity. It does not justify withdrawing the conditional claim.

3. **Low: distinguish sufficient graph coverage from necessity more explicitly.** `inputs/r.tex:78` first
   calls the design sufficient, correctly, but its closing sentence can suggest that absence of a triangle
   prevents calibration. A connected observer graph containing an odd cycle of length five can identify
   positive reliabilities without a triangle. Full coverage of every edge of G is also stronger than needed to
   recover c: calibrated coverage of a connected spanning subgraph suffices. Retain the stated convenient
   assumptions, but say connectivity alone does not guarantee calibration and a triangle is the sufficient
   calibration device chosen here. Neither this wording nor the stronger assumptions invalidate
   `inputs/r.tex:80-110`.

4. **Low: empirical diagnostics should be described as necessary checks, not model verification.**
   `inputs/r.tex:155` appropriately proposes testing moment restrictions. Passing them cannot establish the
   shared latent draw, conditional independence, truthfulness, or contribution semantics. In particular, an
   admissible positive triangle of pair products determines three reliabilities without redundant equality
   restrictions; additional overlaps or repeated edge-stratified populations are needed for meaningful
   overidentification checks. Also distinguish r's missing observer-moment experiment (`inputs/r.tex:149`)
   from P's existing comparator diagnostics: P reports a cycle rate and held-out likelihood
   (`inputs/P.tex:521`) and comparison accuracy (`inputs/P.tex:550-552`). Those are not tests of r's observer
   model. This is a clarification of the proposed empirical scope.

5. **Informational: the implementation limitations are acknowledged and are not theorem defects.** The
   qualifications in `inputs/r.tex:43-45,118-124,134-149,160-161` explicitly leave truthfulness, belief-map
   bootstrapping, finite samples, collusion, and churn outside the identification result. The theorem assumes
   a distribution of reports with the stated noise law; it neither elicits those reports nor proves they
   measure actual contribution. That distinction is sufficient to retain a conditional mathematical draft.

## Independent proof assessment

### Populations and noise model

Fix an orientation e = (i,j), with X_e = +1 meaning i is preferred to j. Set p_e = sigma(c_i - c_j) and m_e =
2*p_e - 1. The score vector is real and finite (`inputs/r.tex:66-76`), hence 0 < p_e < 1. For binary Y, the
conditional mean assumption is equivalent to

P(Y_er = y | X_e = x) = (1 + a_r*x*y)/2.

Consequently 0 < a_r <= 1 is implicit: reliability is the signed correlation parameter, and probability of a
correct observation is (1 + a_r)/2. No missing upper bound creates a valid counterexample. Truthful reporting
means reporting the private noisy observation; it does not mean reporting X without error.

There are distinct observable populations (`inputs/r.tex:78,85,100`). Each observer link supplies a
distribution of paired labels on repeated shared items. The edge mean supplies labels on repeated draws from
that particular edge's target population. These must use the same observer parameters. Different calibration
links can have different latent prevalences and need not share the same individual items. No simultaneously
observed triple is required. Merely comparing the same agent pair on independent redraws is not the
shared-item design.

Read the sampling assumption as written: the noise model holds on each sampled population, and the
edge-specific labels represent that edge's stated distribution. Selection that changes the conditional error
law or substitutes a different target prevalence would violate these premises. Independence across repetitions
is not needed to identify parameters from observable population laws; a law of large numbers or concentration
result would require additional sampling control. The paper explicitly claims no such statistical result.

### Moment factorisation and calibration

On any calibration link, conditional independence gives

q_rs = E[Y_r*Y_s] = E[E[Y_r | X]*E[Y_s | X]] = a_r*a_s*E[X^2] = a_r*a_s.

These are uncentered cross-moments. Centered covariance would instead contain the factor 1 - E[X]^2.
Conditional independence, not unconditional independence of reports, is the appropriate premise. Even if link
populations mix edges, the identical binary conditional laws with edge-invariant a_r preserve this
calculation. An arbitrary latent prevalence cancels.

For the observed triangle r,s,u, q_su > 0 and

a_r = sqrt((q_rs*q_ru)/q_su).

The positive root is forced, and the other triangle reliabilities follow by division. For every path from that
triangle, a_v = q_rv/a_r identifies the next observer. Exact population moments satisfying the model make the
answer independent of path. This proves the calibrated-component conclusion (`inputs/r.tex:85-99`). The
diagonal of the observed label moment matrix is 1, not a_r^2; the rank-one completion refers to off-diagonal
products, not the full observed matrix including its diagonal.

### Edge inversion and score identification

For a calibrated observer on edge e, write b_er = E[Y_er]. Then

m_e = b_er/a_r; p_e = (1 + b_er/a_r)/2; d_e = log(p_e/(1 - p_e)) = c_i - c_j.

Every division and logarithm is defined under the stated assumptions. The first mean must come from the
edge-specific population; a pooled mean over other edges would not suffice. If several calibrated observers
label the edge, their ratios agree under the model. This proves `inputs/r.tex:100-105` directly.

Let B have one row per oriented edge, with +1 at i and -1 at j. Then B*c = d. If another vector c' fits the
same probabilities, B*(c' - c) = 0. On a connected G, this kernel consists of constant vectors, so c' = c +
k*1. Existence and zero sums of oriented differences around cycles follow from the assumed Bradley-Terry
vector; they are not inferred from arbitrary comparison data. This independently proves
`inputs/r.tex:107-109`. Reversing an edge must negate X and Y and replace p by 1 - p; the score difference
changes sign consistently.

### Degenerate cases and graph conditions

- Equal scores give m_e = 0 and p_e = 1/2. Edge means vanish, but calibration products remain positive and
  recover reliabilities. Identification of tied scores is valid; a unique strict ordering of tied agents is
  not implied.
- Perfect observers, a_r = 1, are allowed. Positive reliabilities arbitrarily close to zero remain
  identifiable at population level, but calibration and mean division become poorly conditioned. Zero
  reliability is excluded. If all signs were unrestricted, simultaneous reversal of latent comparisons and
  observer signs would create an orientation ambiguity; the positivity assumption removes it.
- Arbitrarily large finite score differences remain identifiable but make the logit inverse poorly
  conditioned. Values p = 0 or p = 1 are outside the finite-score model. No uniform error rate follows from
  mere positivity and connectedness.
- For observer products alone, log(q_rs) = log(a_r) + log(a_s). A connected graph with an odd cycle uniquely
  determines these log reliabilities. For example, on a five-cycle, a_1^2 = (q_12*q_34*q_51)/(q_23*q_45). This
  establishes that a triangle is not necessary.
- A connected bipartite observer graph generally permits a'_r = t*a_r on one part and a'_s = a_s/t on the
  other, for t near 1 and interior reliabilities. With balanced latent draws, the means vanish and the paired
  binary distributions also remain unchanged. Thus connectivity alone is not a general guarantee. Boundary
  products such as q_rs = 1 can fix parameters even on bipartite graphs, and extra informative means or
  anchors can help; an odd cycle is not a universal pointwise necessity for every richer observation design.
- Disconnected G leaves an independent additive constant in each component; relative component levels are not
  identified. Connected G may be a tree: no comparison-graph triangle or odd cycle is needed. A single ranked
  vertex is vacuously identified modulo translation. Uncalibrated observers outside the designated component
  are not claimed to be identified.

These checks reveal no counterexample satisfying the actual theorem premises. Cases with independent redraws,
unrestricted correlated errors, missing calibrated coverage, or zero reliability are failures of proposed
applications outside those premises.

## What Q and P actually furnish

Q's finite-support construction is explicit in `inputs/Q.tex:1653-1698`: supported types, belief closure,
distinct subjective co-player laws, a quadratic score, utility cancellation, and off-support prohibitions. Its
proof obtains score loss Lambda*||beta_i[t] - beta_i[t']||^2, minimum separation delta > 0, bounded residual
utility gain M, and sufficient scale Lambda >= M/delta (`inputs/Q.tex:1701-1734`). These passages support r's
qualified account in `inputs/r.tex:43-45,118,147`.

Q expressly gives the designer the belief map and permits non-common priors (`inputs/Q.tex:1492,1782`). These
are agents' subjective beliefs, not automatically empirical conditional frequencies. Learning population
reliabilities therefore does not by itself learn the beliefs needed for Q's incentives. Its reporting game is
static, with reports before interim signals and actions (`inputs/Q.tex:1551-1557`), and its incentive
constraint holds other agents truthful (`inputs/Q.tex:1585-1602`). Q does not establish equilibrium uniqueness
or strategic robustness during changing participation. The concrete binary illustration treats types as
private signals with no later learning (`inputs/Q.tex:1738-1777`); it does not establish r's shared-draw
symmetric-flip model for arbitrary comparisons.

P supplies an external LMM comparator receiving the agents' egocentric images (`inputs/P.tex:285-303`),
Bradley-Terry fitting (`inputs/P.tex:313-329`), and terminal-zero softmax potentials (`inputs/P.tex:337-349`).
Its actual interface includes ties with half-counts (`inputs/P.tex:300`), whereas r's theorem assumes binary
labels. A deployment would need a binary sampling channel or a justified tie treatment. There is no
acting-agent comparison-report mechanism here for Q to certify.

P assumes the latent preference vector (`inputs/P.tex:361`) and assumes its equality with Shapley values for
its interpretive proposition (`inputs/P.tex:385-389,751-775`). Thus r correctly distinguishes estimating a
comparator preference from recovering true contribution (`inputs/r.tex:49-50,145`). Q and P do not furnish r's
shared latent item, conditional independence, positive edge-invariant symmetric reliabilities, observer
coverage, or truthful sampling process. These are added assumptions, explicitly set out in r.

To make the convergence qualification concrete, consider three agents with c = (0,0,0), independent
Bradley-Terry labels, K - 1 observations of edge (1,2), and a single observation of edge (2,3). The undirected
comparison graph is connected for every K. The leaf's sole win or loss drives its unregularized fitted
difference to infinity, so a finite MLE does not exist; repeated sampling elsewhere cannot consistently
estimate that leaf difference. This refutes sufficiency of connectedness and total query count alone, not r's
population theorem. It is excluded by a persistent informative sampling condition such as the uniform sampling
invoked in P's appendix. P's local-curvature/Taylor sketch is also insufficient to certify its advertised
finite-sample rate as stated. r need not inherit that rate or repair P's proof to establish its own result.

## Adequacy of qualifications

The strategic caveats are sufficient for the conditional claim. `inputs/r.tex:118-122` explicitly assumes
truthful signals, known separated laws, and bounded gains, and identifies the missing truthful bootstrap.
Cross-fitting cannot create a truthful equilibrium from untrusted initial reports. Without a common-prior or
otherwise justified subjective-belief specification, statistical calibration is even less than the belief
information Q requires. These are missing implementation premises, not algebraic contradictions.

The shaping qualification is correct. For a fixed agent's well-defined state-time potential, sum from t = 0 to
T - 1 of gamma^t*(gamma*psi_(t+1) - psi_t) equals -psi_0 + gamma^T*psi_T. With terminal zero and a common
initial boundary across deviations, all return differences are unchanged (`inputs/r.tex:52-62,124`). A
report-dependent initial potential acts as a boundary transfer. Changes in participation require consistent
per-agent return and boundary accounting; r promises no churn result. Potential shaping can affect learning
without repairing report incentives.

The statistical limitations are also appropriate (`inputs/r.tex:134-143`). Independent latent redraws produce
a_r*a_s*m_e^2 rather than a_r*a_s. For asymmetric errors, writing E[Y_r | X] = alpha_r + beta_r*X introduces
intercept and prevalence terms into products. Correlated errors introduce conditional covariance. These models
generally invalidate the displayed factorisation, although special cancellations can preserve particular
moments. The restrictions are sufficient, not claims that every departure destroys every possible
identification method.

## Bounded primary-source literature check

The four directly relevant bibliography entries (`inputs/r-references.bib:21-59`) were accessible as primary
full-text HTML. I inspected their relevant model, identification, and algorithm passages rather than relying
on search snippets.

- [Ma et al. (2017), Sections 2-4](https://arxiv.org/html/1706.06660): the independent single-coin label
  model, expected worker products, rank-one fitting, and odd-cycle identification are explicit. This directly
  supports r's acknowledgement of the established calibration step.
- [Ma et al. (2019), Sections 3 and 5.1, Theorem 8](https://arxiv.org/html/1904.11608): the model
  distinguishes correct-label probability from signed skill, discusses sign restrictions, and uses a limiting
  graph of repeated interactions. Its learnability characterization includes non-bipartiteness and additional
  instance-class/sign conditions. It supports the graph comparison here; r's short positive-skill population
  proof does not depend on all of that paper's algorithmic guarantees.
- [Nordio, Tarable, and Leonardi, Sections II and IV-B](https://arxiv.org/html/2310.02016): worker-specific
  response probabilities depend on quality differences and reliability, and QUITE alternates quality and
  reliability estimation with graph least squares and MAP steps. This supports r's comparison with established
  heterogeneous-worker ranking. It is not the same shared-random-comparison observation model.
- [Shejole et al., Sections 3-4](https://arxiv.org/html/2608.10045): the response probability is
  sigma(beta_s*(r_w - r_l)); the authors discuss shift/scale nonidentifiability and construct an EM procedure
  with latent-variable augmentation. This verifies r's narrow model/algorithm description. I did not
  independently validate that paper's convergence proofs, and r does not need them for its theorem.

The difference between r's marginal response (1 + a_r*tanh((c_i - c_j)/2))/2 and a worker-temperature logistic
response is substantive. It explains why those ranking papers are related without making their theorems
interchangeable. The inspected literature supports the stated explanatory contribution and the acknowledged
reuse of calibration. It does not establish that the pair-specific composition is itself a publishable
advance, nor does this bounded check establish exhaustive novelty or priority.

## Separate judgments and audit limits

**Correctness:** the central conditional identification claim survives independently reconstructed proof and
degeneracy checks. No fatal mathematical defect was found. No central theorem amendment or withdrawal is
warranted.

**Scope:** retain the mathematically supported conditional draft. Make local corrections to the P attribution,
triangle wording, and interpretation of empirical diagnostics before external circulation. A practical
incentive-compatible replacement for P's comparator remains unproved, as the paper states.

**Novelty and publication:** explanatory value is supported; publication readiness is not established.
Established ingredients and absent deployment do not refute the theorem, but correctness alone does not
demonstrate a sufficient research advance.

This was a focused audit of all of `inputs/r.tex`, its supplied bibliography and Q/P metadata, and the
relevant supplied Q/P model, mechanism, ranking, shaping, proof, and diagnostic passages. Q and P were
assessed from the supplied files; no separate public-version identity check was made. Other references cited
inside Q, P, or the four inspected external papers were not thereby verified. No historical verdicts, other
experiments, or peer notes were consulted. No other agents, repository tests, pipeline changes, or edits to
inputs were used. The audit did not compile the candidate, replicate experiments, prove finite-sample bounds,
or exhaust the literature. Algebraic reconstructions and counterexamples are the reviewer's own; internal
ledger comments and unavailable notes were not used as evidence.
