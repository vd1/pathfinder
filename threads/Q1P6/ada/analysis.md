# Ada's analysis of Q and P

## Bottom line

The abstract-level connection should be changed. Treating MARS-RA as a routine instance of learning-augmented algorithms would conflate different meanings of robustness. P proves concentration of a Bradley-Terry estimator around an assumed latent LMM preference. Q defines robustness as a prediction-independent bound on the downstream objective and repeatedly warns that predictor error does not automatically transfer through a system. The useful joint result is a boundary theorem and audit: under exact potential-based shaping, arbitrary comparison errors do not change the infinite-horizon discounted objective because the shaping terms telescope, while any claim about faster finite-time learning needs a separate stability model for the MARL learner. P supplies neither such a model nor a downstream smoothness theorem.

## Evidence from the papers

P constructs ordered LMM comparisons at every training step (P, lines 285-300), fits a Bradley-Terry MLE (lines 314 onward), and uses the resulting score in a potential. Its Proposition 1 assumes the comparator follows a Bradley-Terry model with latent vector c* and bounds estimation error to c* (lines 361-376). This only controls sampling noise conditional on correct specification. Proposition 2 reaches Shapley values only under the premise c*=v* (lines 383-389), which assumes away semantic bias. P itself calls Shapley value an interpretive reference rather than a practical recovery claim.

Q defines prediction error against a task target and separates consistency, robustness, and smoothness (Q, formal framework beginning near line 300). More directly, Q states that equal predictor errors may perturb different decisions differently (line 945), semantic output requires a typed error interface (line 1179), marginal coverage does not imply downstream cost (line 1204), and semantic reasoning does not improve a guarantee without a new model and proof (line 1230). Its error-propagation proposition requires a metric and sensitivity map at every edge (lines 1097-1105).

## A concrete joint theorem

Let the learned comparison score be c-hat_t, let psi_t=softmax(c-hat_t), and let P's shaping term be F_t=gamma psi_{t+1}-psi_t. For any realized, possibly biased, stochastic, or history-dependent sequence of comparison outputs,

sum from t=0 to T-1 of gamma^t F_t = -psi_0 + gamma^T psi_T.

With P's terminal convention psi_T=0, the entire shaping return is the action-independent initial offset -psi_0. Therefore arbitrary comparison error cannot change the ordering of policies by exact discounted return, provided the potential is well-defined on the relevant augmented state or history and the same consecutive potentials are used. This is a stronger objective-level robustness statement than an error-sensitive curve, but it says nothing about optimization dynamics.

There is a pair-specific obstacle to even this application. P defines c_t in the active-agent space R^{|I^t|}, then subtracts consecutive softmax vectors. When agents enter or leave, |I^t| and |I^{t+1}| can differ, so F_t is not defined as written. A repair must embed credits in a fixed global agent space or specify entrant and exit coordinates, then prove that the resulting per-agent potentials preserve the intended team objective or equilibrium. Q's insistence on typed interfaces therefore identifies a concrete defect rather than merely offering new terminology.

A concrete repair uses P's fixed population N. Define Phi_t in R^n by placing softmax(c-hat_t) on active coordinates and zero on inactive coordinates, set Phi_T=0, and keep a reward ledger for every population member on every transition:

F_t^i = gamma Phi_{t+1}^i - Phi_t^i.

Then, componentwise, the discounted shaping return is -Phi_0^i. For a fixed initial augmented state this shifts every player's payoff by a policy-independent constant, so unilateral payoff differences, Nash equilibria, and the ordering of team policies are preserved for arbitrary comparison outputs. This construction also exposes an implementation choice that P leaves unspecified. P begins with a scalar team reward but adds a vector shaping term. If rewards are recorded only while an agent is active, participation intervals retain entry and exit boundary terms instead of telescoping globally. Those terms can depend on policy. An active-only implementation therefore needs explicit transition ownership or compensating transfers. The fixed-space result is a proposed correctness repair, not a theorem already proved by P.

There are two coherent payoff choices. Per-agent environmental payoffs plus componentwise F_t^i support the unilateral-payoff and Nash-invariance statement above. A scalar team potential supports joint-policy ordering, but naively summing P's softmax credits gives potential 1 at every nonterminal nonempty coalition. That scalar shaping signal contains no comparison information. MARS-RA can therefore matter only through redistributed per-agent learning signals, which makes the missing payoff and learner-interface specification central rather than cosmetic.

For local signal perturbation, softmax is at most 1/2-Lipschitz in Euclidean norm, so if d_t is score error modulo the translation ambiguity, then

norm(F-hat_t-F-star_t) <= (1/2)(gamma norm(d_{t+1}) + norm(d_t)).

Combining this with a corrected Bradley-Terry estimation result and a semantic-bias term would bound reward perturbations. It still cannot bound the performance of MAPPO after N updates without an assumption connecting reward-sequence perturbations to the output policy. This is precisely the missing edge in Q's composition vocabulary.

## Impossibility point

No nontrivial finite-training smoothness curve can follow from P's premises alone. A learner may ignore shaped rewards, amplify tiny reward changes through discontinuous tie-breaking, or fail to optimize at all. These learners share the same comparison accuracy and Bradley-Terry estimation error but have arbitrary output-policy performance. A theorem needs a specified learner and a stability, regret, or convergence premise. Aggregate pairwise accuracy is also insufficient because errors at frequently visited or decision-critical states can matter differently, and the policy changes which states generate later comparisons.

## Problems inside P's estimator claim

The stated concentration result needs repair before composition. Connectedness alone does not give a uniform strong-convexity constant for Bradley-Terry likelihood: curvature also depends on score range and sampling weights, and unregularized MLE can fail to be finite under separated outcomes. P mentions regularized MLE but displays an unregularized objective. Its rates are internally inconsistent: Proposition 1 states a normalized bound that implies a different n dependence from the appendix restatement, while the appendix's final assembly gives yet another dependence. The Taylor expansion is written as an approximation inside a proof. These are not merely presentation details because the graph topology and dynamic range determine the proposed query-versus-error tradeoff.

## Publication assessment

A paper that only labels MARS-RA with Q's consistency-robustness vocabulary is unlikely to contribute enough. A viable focused project would instead study prediction-robust potential shaping in open Markov games, with a finite-time, cost-aware theory and experiment:

1. Define fixed-space potentials, per-agent payoff semantics, and entry or exit reward ownership for changing coalitions.
2. Correct the comparison-estimation theorem and decompose score error into finite-query variance, Bradley-Terry misspecification, and semantic bias to a declared contribution target.
3. Prove pathwise objective invariance and a local reward-signal perturbation bound.
4. Add a MAPPO-specific or abstract learner-stability assumption to obtain a finite-training performance bound, or prove a lower bound showing why comparison accuracy alone cannot do so.
5. Price LMM calls using Q's kappa-augmented accounting and evaluate success as a function of wall-clock or query cost, not accuracy alone. P reports that 50-million-step training rises from 16 hours for MAPPO to 30 hours for MARS-RA (P, line 783), making this empirically consequential.

The strongest question is therefore: under what learner-stability and comparator-misspecification assumptions does K costly semantic comparisons improve finite-time MARL performance, given that exact potential shaping already makes the limiting control objective invariant? This question only becomes visible when Q's interface and composition discipline is applied to P.

## Unresolved

The two supplied papers do not establish a suitable stability theorem for MAPPO, so the positive finite-time bound remains open. The exact applicability of dynamic PBRS also needs careful checking when the LMM output is stochastic and policy-dependent: the pathwise telescoping identity holds, but a Markov-game equilibrium statement may require augmenting state with time, query randomness, and history. It is also unresolved whether MARS-RA's MAPPO implementation records inactive-agent ledger rewards; active-only equivalence needs a compensating-transfer design. Prior-work novelty was not assessed here.
