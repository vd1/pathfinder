# Q and P: payoff-equivalent feedback in LLM double auctions

## What the assigned papers actually contain

[Q](../inputs/Q.tex) is an experiment with LLM buyers and sellers in a finite continuous double auction. Buyers and sellers each know a private reservation price, see the standing quotes and public order history, and are told to maximize their own trading profit (Q, lines 210-278 and 515-570). A round has at most \(300\) iterations (Q, lines 239-259). GPT Large often makes small quote improvements without crossing a profitable spread, and its rounds average \(2.2\) to \(3.8\) trades rather than the equilibrium quantity of \(6\) (Q, lines 316-335 and 359-371).

[P](../inputs/P.tex) is itself a synthesis of different papers. Its labels for Q and P in lines 21-49 refer to a mechanism-design paper and MARS-RA, respectively, rather than to the assigned Q and P. Its peer-calibration theorem cannot be directly applied to the auction: it requires repeated, independent noisy labels of the same latent comparison on an overlapping observer graph (P, lines 64-110), whereas Q records strategic quotes from traders with private reservation prices and a shared public order book (Q, lines 261-278). Q also reports anchoring on an opening quote (Q, lines 397-402). That is evidence of a possible source of shared context effects, although it is not a test of P's conditional-independence assumption for peer labels.

The transferable element is P's potential-shaping identity (P, lines 52-62 and 124). P applies it to cooperative credit assignment; Q supplies a competitive environment in which payoff-equivalent feedback can be tested on inference-time LLM traders.

## Exact strategic benchmark

Consider one auction round with complete public state \(s_t\), a fixed initial state \(s_0\), and terminal time \(T\). Trader \(i\)'s original undiscounted payoff is \(U_i\), its realized trading profit. Pick any state-time potential \(\psi_i(s,t)\), fixed before play, with \(\psi_i(s_T,T)=0\) for every terminal state. Give transition feedback

\[
F_{i,t}=\psi_i(s_{t+1},t+1)-\psi_i(s_t,t).
\]

Pathwise, for every action history,

\[
\widetilde U_i
=U_i+\sum_{t=0}^{T-1}F_{i,t}
=U_i-\psi_i(s_0,0).
\]

Thus each trader's payoff differences across its own strategies are identical for any fixed opponents' strategies. The set of best responses and Nash equilibria is identical. A random initial state independent of play gives the same conclusion conditional on that state. This is a direct use of P's calculation, not a new theorem. Multi-agent equilibrium invariance under potential shaping is also established by [Devlin and Kudenko](https://eprints.whiterose.ac.uk/id/eprint/75111/) and [Lu, Schwartz, and Givigi](https://arxiv.org/abs/1401.3907).

A concrete completion potential is \(\psi_i(s_t,t)=\lambda\mathbf{1}\{i\text{ has traded by }t\}\) for live states and \(0\) at terminal settlement, with \(\lambda>0\). A preterminal trade earns a displayed \(\lambda\) credit and settlement removes exactly \(\lambda\). The true round payoff remains trading profit. The same construction could use a publicly visible spread potential. State variables, transition timing, and final settlement must be identical across arms. If the potential is recomputed with changing parameters, the pathwise cancellation needs to be checked again.

## Publication question and discriminating experiment

**Sharpened question:** Can payoff-equivalent completion feedback change inference-time LLM traders' spread-crossing decisions and market efficiency when the auction state and final profit are held fixed?

Q finds that urgency and execution terms rise in Gemini Large traces when traders cross, but states that this association does not establish the cause of crossing (Q, lines 405-442). Completion feedback supplies a controlled intervention on that proposed process. Trace vocabulary can be a secondary outcome, but it should not replace observed quotes and realized profit.

Randomize matched auction seeds and agent populations between two prompts. Show both arms the same state, clock, reservation price, public history, numerical completion indicator, and exact final profit rule. In the treatment, label the indicator's changes as provisional reward credits with explicit terminal reversal. In the control, show the same numbers as bookkeeping information without reward framing. Settle credits before the next round. Check that the realized total shaping payment is \(0\) for every trajectory, and measure crossing at profitable standing quotes, quote increments, trade count, and allocative efficiency. A treatment effect would show sensitivity to the path or framing of feedback despite identical final profit; it would not by itself establish a preference change or a failure of game-theoretic equilibrium reasoning. Prior multi-agent work already shows that shaping can alter learning paths without changing equilibria, so the specific target here is fixed-weight LLM behavior in Q's market.

Make realized surplus divided by the available surplus the primary welfare endpoint, following Q's own efficiency definition (Q, lines 295-300). Trade count and price dispersion are separate diagnostics. In Q's symmetric value schedule, five positive-surplus matches yield \(2.50+2.00+1.50+1.00+0.50=7.50\) total surplus; the sixth equilibrium trade has zero surplus (Q, lines 210-237). Hence a five-trade path can be fully efficient, and prices can vary while surplus is maximal. A completion prompt that merely increases trade count need not improve welfare.

Add a separate controlled decision probe to make the interpretation sharper. Use the final actor in the fifth and final round, or explicitly rule out any continuation payoff or later history effect. Disclose to both arms that a resting opposite-side quote yields strictly positive profit if crossed and that no later market action can fill an uncrossed order. Put a forced settlement step after this decision so a completion credit can be displayed and then reversed. In that state, crossing strictly dominates an uncrossed quote under the stated profit objective. Q's original prompt gives the round number and mentions an order cap, but does not explicitly tell agents the cap is \(300\) or that a particular turn is final (Q, lines 539-566). Earlier-round quotes also enter future histories (Q, lines 261-266 and 543-548). Therefore Q's late stalling cannot itself be called a dominated final-turn choice.

The experiment has not been run. A publication claim would require a measured effect, replication across model families and roles, a clear account of prompt sensitivity, and a check that information and final payoff truly match. A null result is informative too: it would reject this specific feedback-framing intervention as an explanation or remedy for Q's stalled trading under the tested conditions.

## Prior-work search and remaining limits

Queries run: `potential based reward shaping LLM agents double auction trading experiment payoff equivalent`; `LLM agents reward framing payoff equivalent potential shaping auction market`; `potential based reward shaping multi agent Nash equilibria stochastic games theorem`. The search identified the established invariance papers above and a related [LLM-guided shaping study in a continuous double auction](https://arxiv.org/abs/2508.18610). I do not infer novelty from the absence of a matching result in these queries. P's rank calibration and the general shaping theorem are established ingredients. The proposed contribution, if supported experimentally, is a controlled behavioral finding about Q's specific market failure.
