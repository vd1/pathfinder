# A provable interface between peer elicitation and rank aggregation

## What the papers do and do not compose

The abstract-scan hypothesis is false for the mechanisms as written. P's acting agents submit no contribution reports. An external LMM compares their egocentric observations (P, lines 279-316). Q instead scores a supported type report against the conditional distribution of co-player type reports and needs distinct types to induce distinct peer-report laws (Q, lines 1659-1718). Q therefore cannot certify strategic robustness of current MARS-RA.

P's statistical guarantee also stops short of contribution truth. It assumes that all comparisons follow a common Bradley-Terry vector and proves recovery of that vector on a connected graph (P, lines 361-376). Its Shapley interpretation assumes that the latent vector already equals the Shapley vector (P, lines 380-389).

The pair does, however, expose a precise missing interface: truthful heterogeneous peer signals must be converted into observations of one latent Bradley-Terry ranking.

## A calibrated heterogeneous-observer model

Fix a time and an active-agent comparison graph G. For edge e = (i,j), let the latent correct comparison X_e be in {-1,+1}, with

Pr(X_e = +1) = sigma(c_i - c_j).

Peer observer r has reliability a_r in (0,1]. Conditional on X_e, its truthful signal Y_er in {-1,+1} is an independent symmetric-noise observation satisfying

E[Y_er | X_e] = a_r X_e.

Thus observer accuracy is (1+a_r)/2, and observers may have different accuracies. Assume at least three observers overlap on calibration items, all a_r >= a_min > 0, score differences are bounded so probabilities lie in [kappa,1-kappa], and G has Laplacian gap lambda_2 > 0.

For incentives, regard an observer's private signal and capability class as its finite Q-type. Assume Q's belief closure and peer-law separation. If Delta is the smallest squared separation and B bounds the gain from a false report, Q's quadratic peer score with weight Lambda gives strict truthful margin

g = Lambda Delta - B > 0.

This is a specialization of Q's calculation: a false supported report loses Lambda times the squared distance between peer-report laws, while its other utility gain is at most B (Q, lines 1704-1734).

## Interface identification result and finite-sample target

**Identification theorem.** Under the model above:

1. Observer reliabilities and every edge probability are identified without observing X_e or a contribution ground-truth label.
2. With truthful reports, a calibrated Bradley-Terry estimator identifies c up to an additive constant.

**Finite-sample theorem target.** If every comparison edge and every observer-overlap link has enough samples, a bound should decompose into ranking noise, calibration noise, and unilateral approximate-response error. A schematic form is

   ||c_hat-c||_2 / sqrt(n) <= C_G [sqrt(n log(n/delta)/K) / a_min + sqrt(log(R/delta)/L) / a_min^3],

   with probability at least 1-delta. This display is not yet a proved constant-tracked bound. A formal statement needs minimum per-edge and per-overlap counts, a condition number for the agent comparison graph, and a separate condition number for the observer-overlap graph.
3. Against a unilateral epsilon-best response while peers remain truthful, the target bound gains a contamination term of order C_G epsilon/(g a_min). This does not cover coordinated deviations. Agent churn affects both graph condition numbers and the available overlap; if overlap falls below three or the comparison graph disconnects, identification fails.

The powers of a_min are conservative. The important content is the decomposition into ranking noise, learned calibration, strategic contamination, and churn-conditioned connectivity.

## Proof

Write m_e = E[X_e] = 2 sigma(c_i-c_j)-1. Conditional independence gives

E[Y_er] = a_r m_e,

E[Y_er Y_es] = a_r a_s for r != s.

For any overlapping triple r,s,u, positivity of the reliabilities fixes the usual label-swap ambiguity and yields

a_r = sqrt(E[Y_erY_es] E[Y_erY_eu] / E[Y_esY_eu]).

The other reliabilities follow along the connected observer-overlap graph. Then m_e = E[Y_er]/a_r and p_e = (1+m_e)/2. This proves identification without X_e labels. Finally, logit(p_e) = c_i-c_j. A connected G identifies c modulo a constant.

For the finite-sample target, empirical first and second moments are averages of bounded variables, so Hoeffding bounds them uniformly at rates set by the minimum calibration-link and comparison-edge sample counts. The triple-ratio map is Lipschitz away from zero; since a_r >= a_min, propagation through that map costs at most a constant times a_min^-3. Errors also propagate through the observer-overlap graph. Division by estimated reliability costs a_min^-1. The logit map is Lipschitz on [kappa,1-kappa]. Solving edge differences for c applies the inverse agent-comparison Laplacian on the zero-sum subspace. Turning this proof sketch into a theorem requires tracking both graph operators and the sample allocation. This is the heterogeneous calibrated counterpart of P's Hessian/Laplacian argument (P, lines 684-735).

Q's score gives every pure false report payoff loss at least g when the peer-report law remains the truthful beta distribution. If one reporter uses an epsilon-best response and randomizes falsely with probability alpha, expected regret is at least alpha g, hence alpha <= epsilon/g. Replacing an alpha fraction of bounded labels shifts each empirical moment by at most order alpha. Applying the same Lipschitz argument suggests an added term of order C_G epsilon/(g a_min). If peers deviate together, their report law changes and this margin need not survive; the argument offers no collusion robustness.

## Scope and failure tests

This theorem is not implied by either paper. Q supplies the strict reporting margin, but no common latent-ranking identification. P supplies the graph-conditioned ranking step, but assumes a homogeneous trusted comparator. The moment factorization above is the new bridge.

The model is falsifiable. It implies that cross-observer products are edge-invariant: E[Y_erY_es] = a_r a_s. MARS-Bench can test that restriction across tasks, pairs, partial views, and entry or exit events. If it fails, the next result must allow edge-dependent asymmetric confusion matrices or correlated peer errors. With unrestricted observer-by-edge confusion, a latent ranking is not identified from reports alone.

The result also does not solve Q's practical belief-map requirement or collusive equilibrium selection. Q explicitly assumes the designer knows the conditional-belief map (Q, lines 1779-1782), and its framework is static, with dynamic mechanism design left open (Q, lines 2446-2457). Those are substantive limitations, not implementation details.

## Publication question

The question is changed from "does Q explain why MARS-RA resists strategic misreporting?" to:

> Can strategically elicited, heterogeneous partial-view comparisons identify a common contribution ranking without contribution labels, and how do calibration error, approximate incentives, and churn jointly limit recovery?

The symmetric-noise theorem gives a positive baseline that is more than a restatement of P. A publishable paper would test its moment restrictions on MARS-Bench and then seek the smallest relaxation needed by the data. The main unresolved point is whether realistic partial-view observers satisfy enough conditional independence for label-free calibration; if not, extra anchors or structural view models are necessary.
