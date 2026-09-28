# Risk-certificate deepening: a synthetic routing decision

## Scope and ancestry

Authorized by the user's request to proceed with deepening, after opening
Recursive Science. This is a supervisor-led worked application, not another
QP generation or a new independently reviewed paper. Historical campaign
outputs remain unchanged. The parent is the clarified recursive Q1P2 paper:
`../2026-09-28-recursive-extension/reviewed/recursive-Q1P2-v2/paper.tex`.
Its hash will be recorded with the numerical results.

## Question and model fixed before execution

Can a realised-data obedience certificate justify a useful deployment after
charging for the samples and a fallback? This is a synthetic routing model,
not an empirical claim about a real transport or computing system.

There are equally likely signals 0 and 1 and actions A and B. The fixed
policy prescribes A at signal 0 and B at signal 1. At each signal the
prescribed route has loss 2 times a Bernoulli variable with probability p_s;
the alternative has constant loss 1. The agent uses upper-tail CVaR with
tail mass 1/2. Loss is in [0,2]. A reward depends only on the action.
Weak obedience uses recommendation-following tie breaking.

Planner operating cost is 0.2 when deploying the policy. Expected reward
is averaged over the two signals. A conservative loss surcharge of 2 is
charged whenever the deployed reward fails any true obedience constraint.
Fallback costs 1, is externally available, needs no agent obedience, and
does not use the sampled certificate. Rewards have cap 0.6. These are
declared synthetic costs, not inferred social welfare or a competitive ratio.
At most one decision follows the learning batch.

Compare the parent's uniform four-cell error box (4m charged draws) against
an application-aware box with the safe alternative known exactly (2m draws).
The latter assumption requires an actual deterministic service contract or
a justified model; it cannot be inferred from a few constant observations.
Unknown cells have independent Bernoulli samples from a conditional simulator.
This presumes paid counterfactual access, not merely on-policy deployment logs.

## Fixed design

- Confidence failure probability: 0.05 per fixed-batch decision.
- Scenarios (p_0,p_1): free (0.1,0.1), paid (0.3,0.1), near-boundary
  (0.35,0.149), boundary (0.35,0.15), infeasible (0.35,0.2).
- Per-unknown-cell batch sizes: 250, 1000, 4000, 16000, 64000, 256000.
- 2000 independent batches per scenario and size, with seed 20260928.
- Pair access regimes using the same empirical risky losses within a trial.
- Prices per draw: 0.000001 and 0.00001, in planner-cost units.
- Report deployment, refutation, abstention, budget-uncertainty frequencies,
  false definitive decisions, coverage failures, and mean total cost.

Compute binomial counts directly; this is distributionally identical to
sampling the individual Bernoulli losses. Deterministic safe-cell samples
are still charged in the uniform baseline. Confidence claims are per trial,
not simultaneous over this entire grid. The grid does not authorize choosing
a batch adaptively with unchanged fixed-batch confidence radii.

## Decision rule and validation

Solve the two-action reward interval exactly. Use upper risk differences
for support and lower risk differences for refutation. Failure of a robust
budget check leads to fallback, not a claim of true budget infeasibility.
Other inconclusive trials also use fallback. The least nonnegative reward
has one zero coordinate. Check every simulated definitive decision against
the true utility array and report any errors rather than excluding trials.

Derive the oracle cap and a conditional expected-cost bound analytically.
Test the implementation on exact examples and confidence-box corners before
simulation. Preserve executable code, machine-readable results and the
interpretive note. Numerical frequencies do not prove a confidence theorem,
and a favourable chosen instance does not establish general usefulness.
