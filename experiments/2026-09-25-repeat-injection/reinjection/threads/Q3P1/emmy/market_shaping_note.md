# A payoff-equivalent test of late trading in Q's double auction

## Source identities and question

The assigned Q is *Competitive Market Behavior of LLMs*. It studies a continuous double auction with 11 buyers, 11 sellers, five rounds, and a cap of 300 iterations per round [Q, lines 219-259](../inputs/Q.tex). The assigned P is *From Truthful Peer Signals to Contribution Rankings*. Its own references to "Q" and "P" denote two earlier papers, so its incentive and rank identification results do not directly describe the assigned market [P, lines 24-38](../inputs/P.tex).

Q reports that GPT Large agents often improve quotes by one cent until the round ends, with only 2.2 to 3.8 trades per round and efficiency between 0.36 and 0.67 [Q, lines 316-320 and 359-371](../inputs/Q.tex). P gives the exact accounting identity for a terminal-zero potential [P, lines 52-62 and 124](../inputs/P.tex). Together they suggest a controlled question: can feedback that changes the path presentation while keeping each trader's final payoff fixed induce more timely crossings from fixed LLM traders?

## What the identity does and does not establish

Let a full five-round experiment be one finite game with common initial state \(s_0\). Trader \(i\) receives original undiscounted profit \(U_i\). Choose a state-time potential \(\psi_i(s_t,t)\), set its final value to zero on **every** terminal history, and add \(F_{i,t}=\psi_i(s_{t+1},t+1)-\psi_i(s_t,t)\) at each step. Then, path by path,

\[
\widetilde U_i
=U_i+\sum_{t=0}^{T-1}F_{i,t}
=U_i-\psi_i(s_0,0).
\]

With the same initial state in both arms, the added term is independent of every player's strategy. All best-response comparisons and equilibria of the exact game therefore remain the same. This is an application of P's telescoping identity, and prior work already proves multi-agent equilibrium invariance: [Devlin and Kudenko (2011)](https://pure.york.ac.uk/portal/en/publications/theoretical-considerations-of-potential-based-reward-shaping-for-/), [Lu, Schwartz, and Givigi (2011)](https://arxiv.org/abs/1401.3907). It is not a new theorem.

This requires full-episode accounting, or a per-round potential whose initial value is the same on every possible history. Resetting a general potential at each round could introduce a prior-action-dependent next-round initial term, because Q gives agents their previous-round history [Q, lines 261-266 and 543-548](../inputs/Q.tex). A simple safe choice is a provisional completion credit: set \(\psi_i(s_t,t)=\lambda\mathbf{1}\{i\text{ has traded}\}\) in live states and zero at settlement. Its initial and terminal values are both zero in every round. For Q's undiscounted profit objective, use unit discount. If the treatment's potential uses hidden reservation values or future events, it also leaks information. The completion indicator and clock should be visible in both arms.

## A decisive state-level diagnostic

At a known final opportunity in the fifth and final round, suppose a buyer with value \(v_i\) faces a standing ask \(a^\star<v_i\). A crossing bid executes at that ask and gives profit \(v_i-a^\star>0\). Any noncrossing action gives zero, because the experiment ends immediately. Thus crossing strictly dominates delaying at this particular state. The seller case is symmetric: a standing bid \(b^\star>v_i\) yields profit \(b^\star-v_i>0\) when crossed. For earlier rounds, a trade can change subsequent public history, so this strict conclusion would need an added no-continuation-effect assumption.

The diagnostic does **not** establish that Q's observed late noncrossings are mistakes. Q's method fixes the 300-iteration cap [Q, lines 247-259](../inputs/Q.tex), but its displayed prompts give the round number and history without an explicit numerical cap or current iteration [Q, lines 532-565](../inputs/Q.tex). An agent that does not know it has the final opportunity may reasonably hold out. Nor does the diagnostic say early crossing is always optimal; waiting can improve an agent's price.

The smallest experiment is to replay comparable profitable-book states with the final opportunity explicitly announced in both arms. Randomize only the presence of a fully disclosed potential-feedback account, including the terminal reversal. Keep the available state data, model, sampling, and actual final profit fixed. Measure crossing frequency and the lost private profit on failures at these final states; separately measure complete-round surplus and price dispersion in ordinary long-run simulations. A treatment effect would show sensitivity of a fixed LLM policy to payoff-equivalent feedback, not a change in rational incentives. No effect would leave other causes open. Because Q uses fixed prompted LLMs rather than reinforcement-learned policies [Q, lines 280-287 and 515-565](../inputs/Q.tex), this is a test of feedback framing at inference time, not a literal evaluation of P's reinforcement-learning method.

Use realized surplus as the primary market outcome. In Q's value schedule, the five strictly positive-gain pairs can realize the full maximum surplus of \(7.50\); the sixth competitive-quantity trade has zero gain. Their prices can vary within reservation bounds, so five trades and nonzero price dispersion can coexist with full efficiency. Thus trade count and distance from the quoted equilibrium price are useful diagnostics but do not uniquely determine allocative efficiency [Q, lines 219-237 and 295-300](../inputs/Q.tex).

## Independent information limit

P's label-free calibration assumes observers have conditionally independent noisy reports of the same latent binary comparison, with repeated overlap data [P, lines 66-109](../inputs/P.tex). Q instead gives each trader its own reservation value and a public order history; its welfare metric needs the unobserved buyer values and seller costs [Q, lines 261-300](../inputs/Q.tex). Public orders are strategic actions, not samples from P's observer model.

There is a simple nonidentification example within Q's fixed reservation-value multiset. Buyer A trades with a seller of cost \(0.75\) at price \(2.00\); buyer B does not trade. Assign \((v_A,v_B)=(3.25,2.25)\) in one world and \((2.25,3.25)\) in another. Let all public actions be the same, which is feasible because A's purchase is profitable under either assignment. The observed tape and maximum possible surplus are identical, but realized surplus from this trade is \(2.50\) in the first world and \(1.50\) in the second. The construction does not rule out welfare measurement by Q's experimenter, who knows the values, or by new truthful private-value reports. It rules out identifying welfare from the public tape alone; peer calibration cannot manufacture a missing signal.

## Assessment

The strongest pair-specific lead is an experiment separating slow, bounded LLM decisions from changes in the strategic game. The mathematical no-go is established already, and Q's reported aggregates do not show how often a profitable known-final opportunity was missed. A publication would need a preregistered replay or new runs with both arms receiving the same clock and state information, pathwise verification of payoff equivalence, and a credible effect on behavior or a useful negative result. The public-tape example is a design constraint for any extension that tries to use P's peer rankings to score market welfare.
