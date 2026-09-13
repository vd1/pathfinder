# A behavioral revelation gap for LLM contracts

## Verdict

The abstract-level connection should be replaced. P's natural-language treatment does not let an agent reinterpret or counterfeit its commitment. An external judge enforces the retained negotiation at every move, and its measured error rate is only \(3/1155=0.26\%\), with all errors false positives (P, lines 282--286 and 1423--1426). Q's counterfeiting restriction instead concerns infeasible upward type reports backed by hard evidence (Q, lines 299--303).

The promising joint question is sharper:

> Do LLM agents exhibit a behavioral revelation gap, in which mechanisms with the same payoff-relevant mapping induce different outcomes solely because one displays the commitment as natural language and the other as compiled code?

## Why the pair supports this question

Q's multi-agent revelation principle states \(\mathcal O_n=\mathcal O_n^{\mathrm{IC}}\) (Q, lines 1618--1642). Its construction replaces an indirect mechanism by a direct recommendation over signal-contingent plans. The proof relies on equilibrium optimization: an agent can copy the corresponding strategy, and incentive compatibility makes truthful reporting and obedience optimal. The representation used to convey a payoff-equivalent mechanism has no independent causal role.

P supplies evidence that this abstraction may fail behaviorally. Programmatic Trading and NL-Trading begin with the same style of negotiation (P, lines 269--286). Contract use is almost equal, at about \(2.60\) covered tiles per game, while on mutually dependent boards the probability that both agents finish is \(0.79\) under Programmatic Trading and \(0.46\) under NL-Trading (P, line 421). These boards require two chips from the partner for each player, so the average contract is incomplete. Additional trade is necessary. Yet agents make fewer proposals and acceptances under NL-Trading, and cite the insufficient contract when declining trade \(94\%\) of the time, versus \(74\%\) under Programmatic Trading. P interprets this as over-anchoring.

This is not yet a clean representation effect. Negotiations are rerun across treatments, and equality in average realized coverage does not establish equality of terms, histories, or contingent payoffs. P therefore motivates but does not identify the behavioral revelation gap.

## Publication-grade construction

For each completed negotiation transcript \(h\), compile a canonical coverage function

\[
e_h(i,s,a)\in\{0,1\},
\]

where \(e_h=1\) means that agent \(i\)'s proposed move \(a\) in state \(s\) triggers the contracted transfer. Freeze both this function and all penalties. Randomize only the interface shown to the acting agents:

\[
z\in\{\text{canonical prose},\text{JSON}\}.
\]

Both renderings must be generated losslessly from the same canonical fields and contingencies. Full-transcript and hidden-availability arms can diagnose context and salience effects, but they change the agent's information and are not isomorphic mechanisms. Every arm must call the same \(e_h\), so for every history and action the material payoff and feasible-action mapping coincide. Reuse the same board, model, transcript, sampling controls, and role assignment across arms.

Under Q's equilibrium model, a bijective relabeling preserves the equilibrium outcome set. It does not require an LLM to select the same equilibrium in both renderings. The primary test should therefore use decision nodes at which a supplemental trade is strictly payoff-improving under every relevant continuation, or measure action regret against an exact CT planner. A systematic contrast

\[
\Pr(\text{strictly suboptimal refusal}\mid h,z=\text{JSON})
\ne
\Pr(\text{strictly suboptimal refusal}\mid h,z=\text{canonical prose})
\]

tests the optimization and strategy-copying premise without relying on equilibrium selection. Both-finished and residual-trade rates remain useful secondary outcomes. A gap does not refute Q's mathematical theorem. It rejects the empirical adequacy of stable utility maximization and unrestricted strategy copying for these LLM agents.

A useful theory extension is cognitive implementability. Let \(\kappa(z,h)\) map a displayed mechanism into the policy representation the model actually uses. To keep this from becoming a label attached after observing failure, estimate \(\kappa\) on held-out contract-comprehension probes under a fixed inference and token budget, then preregister its predictions for unseen boards. A cognitively direct mechanism must preserve both material incentives and the induced policy representation. P's over-anchoring suggests that natural-language commitments may compress into a coarse rule such as “the contract handles cooperation,” while JSON exposes uncovered obligations and preserves fallback trading.

## Falsification and scope

The claim fails if the matched-semantics intervention eliminates the gap. That result would locate P's original difference in negotiated content, judge semantics, or sampling noise rather than representation. It would still be informative, because it would reject the over-anchoring explanation currently offered by P.

The strongest contribution is therefore not “formal contracts prevent counterfeit commitments.” It is a controlled test of the behavioral premise needed to transport Q's revelation logic to LLM agents, plus a representation-aware notion of implementation if that premise fails.
