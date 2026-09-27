# Matched information states in Q's auction

## Question and source passages

The sharpened question is whether Q's measured efficiency loss can be divided into an information
limit and a decision rule gap. Q gives each selected trader its own reservation price, the best bid
and ask, public market history, and its own history (Q.tex, lines 261-278). It compares realized
surplus with the full-information maximum (Q.tex, lines 295-305), and reports that slow spread
crossing suppresses trades for GPT Large (Q.tex, lines 360-361 and 363-375). P supplies a
conditional method: when the observable history is identical in two hidden states but the required
actions differ, an observation-only receiver cannot guarantee both outcomes (P.tex, lines 43-71).
P's application concerns handover, not auctions.

## A random-schedule counterexample under Q's matching rules

Q fixes eleven seller costs and eleven buyer values at \(0.75,1,\ldots,3.25\) and selects each
invited agent uniformly from agents who have not traded (Q.tex, lines 210-219 and 241-259).
Consider a first-round history with seven earlier trades. One traded seller \(S_3\) sold to the
buyer of value \(3.25\) at price \(3.12\). In state A its cost was \(3\); in state B its cost was
\(1\). Both trades respect the reservation prices. The other six traded sellers have costs
\(0.75,1.25,1.50,1.75,2,2.25\), and can trade profitably with buyers of values
\(1.50,1.75,2,2.25,2.50,2.75\), respectively, in suitable pairings. The same prices and
public history can occur in both states. Seller \(S_3\) is now inactive.

Four buyers and four sellers remain. Buyer \(B\) has value \(3\); the other buyers have values
\(0.75,1,1.25\). Seller \(S_1\), cost \(2.50\), has the standing ask \(2.50\); the standing bid is
\(1.25\). Seller \(S_2\) has cost \(1\) in A and \(3\) in B. The other active sellers cost
\(2.75,3.25\). Swapping \(S_2\)'s cost with inactive \(S_3\)'s cost preserves Q's full fixed
cost multiset. Choose a common visible history in which \(S_2\) has not made a cost-revealing
quote. Q's selection with replacement makes this feasible, even though it may be rare near the
iteration cap. The history and \(B\)'s information are identical in A and B. Six invitations
remain, and their identities are still random.

Assume that agents do not take loss-making trades, that \(S_2\) crosses a profitable standing bid
if selected, and that after an initial noncrossing bid \(B\) may cross \(S_1\)'s ask if selected
again. If \(B\) bids \(2\), then in A the first selection of \(S_2\) causes a trade worth
\(3-1=2\) in welfare. No other agent can profitably cross or improve that bid before this trade.
With eight active agents, the chance of selecting \(S_2\) at least once in six invitations is
\(1-(7/8)^6\), so waiting gives A expected welfare at least
\(2[1-(7/8)^6]>1.10\). In B no seller can profitably cross a bid below \(2.50\). If \(B\)
starts with any noncrossing bid, the only profitable remaining transaction requires \(B\) to be
selected again and cross \(S_1\). Its expected welfare is at most
\(0.50[1-(7/8)^6]<0.28\).

If \(B\) crosses the ask immediately, its trade with \(S_1\) yields welfare \(0.50\) in either
state. In A, any later trade involving \(S_2\) and the remaining buyers adds at most \(0.25\),
so crossing yields at most \(0.75\). In B, crossing yields exactly \(0.50\), since the remaining
buyers value the good below every active seller's cost. Thus A strictly favors an initial
noncrossing bid and B strictly favors crossing, even before the future random invitations are
drawn. The conditional limits follow from the stipulated continuation policy; they are not
estimates of Q's actual agents. The same action distinction also holds for \(B\)'s private profit:
bidding \(2\) in A yields expected profit at least \(1-(7/8)^6>0.55\), while crossing yields
\(0.50\); in B a noncrossing first bid yields at most \(0.50[1-(7/8)^6]<0.28\).

The oracle in this comparison knows whether A or B holds but does not know future invitations.
For an illustrative equal prior, even allowing the observation-only policy to adapt to later
public events, its expected welfare regret is at least
\(\frac12\min\{2[1-(7/8)^6]-0.75,\;0.50-0.50[1-(7/8)^6]\}>0.11\).
This bound applies only to the constructed history and continuation policy. It is not a bound
on Q's reported market efficiency.

An earlier two-seller swap, where both sellers remain active, gives an illustrative gap of
\(0.25\) only after conditioning on which seller receives the final invitation. Under Q's
uniform scheduler, otherwise symmetric active sellers are exchangeable, so that calculation
does not establish an ex-ante gap from private costs alone. The construction above swaps an
active and an inactive seller to break this symmetry while keeping the scheduler random.

## Empirical threshold

The counterexample proves only that an information limit is possible within Q's rules. It does not
show that such ambiguity is common, or that it explains GPT Large's measured failure to cross
spreads. A test would clone actual Q decision histories, construct hidden value assignments
consistent with the entire visible history and Q's fixed value multiset, then integrate over Q's
actual random scheduler under a stated opponent continuation rule. It should compare the LLM with
an information-matched simple or optimized trader and with a hidden-value-informed control.
Evidence for an information explanation requires nontrivial regret among the information-matched
controls at decision states that actually occur. Evidence for a decision rule problem would be the
LLM losing trades that the information-matched controls can profitably complete.

This test needs explicit assumptions about the hidden-state prior and other traders' continuation
policies. A public history that is mechanically compatible with two assignments may have tiny or
zero probability under a specific agent policy, so replay alone does not identify its posterior
weight. The test must also distinguish individual profit regret from aggregate welfare regret. Neither
input provides the state-conditioned data or counterfactual experiment. A classical baseline already
exists: Gode and Sunder's budget-constrained zero-intelligence traders achieve high efficiency in
their double auctions, so an information-matched baseline alone is not a new result.

Source: [Gode and Sunder (1993)](https://www.journals.uchicago.edu/doi/pdf/10.1086/261868).
