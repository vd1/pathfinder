# F3. Does P's objective control network tail risk? (Q Sec. 6 composition lens)

P motivates CVaR by system-level tail events ("a localized power surge can cascade into a grid-wide blackout",
P Sec. 1) but optimises A(x) = (1/m) sum_i CVaR_alpha[J^i(x, xi^i)], the average of local tails. Take the system
risk to be S(x) = CVaR_alpha[(1/m) sum_i J^i(x, xi^i)] (common alpha, joint law of the xi^i).

## What transfers
Subadditivity and positive homogeneity give S(x) <= A(x) for every x. So P's output carries a one-sided
certificate: S(x_P) <= A(x_P) <= min_x A + O(delta + e_s) (F1 order). In Q's additive-composition proposition
(Q Prop. "Expository condition: additive composition") this is the direction that needs no benchmark relation.

## What does not transfer
Q's proposition needs OPT_sys >= beta sum_i OPT_i with beta > 0 to turn component guarantees into a system ratio.
Here beta can be 0. Example (P's assumptions hold, losses linear in x, bounded): x in [0,1] (shift to contain a ball),
xi = +1 or -1 with probability 1/2, alpha <= 1/2, a in (0,1),
  J^1 = (1-x) a + x xi,   J^2 = (1-x) a - x xi.
Then CVaR_alpha[x xi] = CVaR_alpha[-x xi] = x, so A(x) = (1-x) a + x, minimised at x = 0 with A = a.
The system loss is (1-x) a, so S(x) = (1-x) a, minimised at x = 1 with S = 0.
P's decision has system risk a against an optimum of 0: the ratio is unbounded and the additive gap is a.
The mechanism is hedging across agents. P's objective rewards each agent for its own tail and cannot see offsets.

## A remark in P's appendix
P: "The equality holds if and only if the random variables J_1, ..., J_m are positively correlated and move
entirely in tandem." Comonotonicity is sufficient, but it is not necessary. Counterexample: four equally likely
states, X = (0, 1, 0, 5), Y = (1, 0, 0, 5), alpha = 1/4. Then CVaR(X) = CVaR(Y) = 5 and CVaR(X + Y) = 10, so equality
holds, yet X and Y are not comonotone (X rises and Y falls from state 1 to state 2). Equality needs a common alpha-tail
scenario set, not tandem movement everywhere. P's label for the gap, "the cost the system incurs to enable
distributed computation", also misreads it: A and S are different objectives, and the gap is a modelling choice,
not an overhead of distribution.

## Open question visible only with both papers
In the cascade regime that P uses as motivation, the tails co-move, so A is close to S and P's surrogate is faithful.
In the hedging regime, A can be arbitrarily wrong for S. A distributed method for S needs the joint scenario
(synchronised samples) and one scalar consensus on the network-average loss per scenario. Under tau-lifting (F2),
the shared threshold tau becomes a consensus variable next to x, whereas the plug-in approach would need the whole
empirical distribution of the network-average loss. I have not analysed this.
