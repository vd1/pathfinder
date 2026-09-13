# What this pair can establish, and what a contract experiment must isolate

My judgment is that the abstract transplant should be replaced. The supported question is whether agents
mistake a limited contractual commitment for a complete policy, suppressing profitable actions that remain
permitted. P suggests this failure but does not identify it causally. Q supplies an already enforced market in
which the same error can be tested without attributing improvements to protection from post-trade defection.
This is an empirical publication candidate, not an established finding or a verified novelty claim.

## Evidence and limits

Q, Trading Mechanism, lines 241-259: each agent trades at most once per round; a crossing quote executes
immediately at the resting price and both agents exit. Q lines 367-371 document small quote increments and
reluctance to cross even when a profitable trade exists. Q lines 435-442 explicitly caution that reasoning
traces do not identify causes. Its private-value environment also differs from P's generally visible
inventories and paths (P lines 1626-1644; information ablation at 683-691).

P distinguishes automatic tile coverage (269-277), natural-language interpretation by a judge (280-286), and
terminal reward transfers (289-302). These are different interventions. In regular trading, P lines 1381-1387
report normalized joint reward of \(0.64\) for natural-language contracts against \(0.93\) without contracts
on mutually dependent boards. Compared with programmatic contracts, natural-language contracts have similar
mean executed coverage, \(2.60\) versus \(2.58\), but fewer trades, \(1.95\) versus \(3.28\). Contract
references occur in a larger share of explanations for declining trade, \(86\%\) versus \(60\%\).

The last comparison is suggestive, not a causal mediation result. Equal means do not match covered tiles, path
feasibility, contract quality, or bargaining histories. Executed coverage is itself an outcome. P's judge
audit (1424) measures errors among approved moves, so it does not exclude false negatives. These are
independently confirmed objections shared with ada in the ledger.

## A constructive bound: regular trading achieves P's both-finish benchmark

P's initial inventories are fourteen chips of the player's own color and two green chips (190 and 1560-1566).
A shortest route across the board uses six moves, of which five enter red or blue tiles and one enters the
green goal. The start is not charged.

Before moving, exchange five red chips for five blue chips. The resulting inventories are

\[
I_R=(9R,5B,2G),\qquad I_B=(5R,9B,2G).
\]

Both inventories cover every shortest route on every valid board. Each player starts movement with sixteen
chips, consumes six, and finishes with ten. P's reward formula (227-232) gives

\[
r_R=r_B=20+5(10)=70,\qquad R=140=R_{\max}.
\]

Thus regular trading already attains the maximum joint reward conditional on both players finishing.
Contracts can increase realized reward by changing behavior, information, or incentives. This construction does not
show agents will propose or accept it, nor does it resolve the delayed Pay-for-Partner problem. It applies to
regular atomic chip exchange.

There is also an explicit strictly beneficial regular trade for every asymmetric board. Give the independent
red player six blue chips in exchange for five red chips. Inventories become

\[
I_R=(9R,6B,2G),\qquad I_B=(5R,8B,2G).
\]

Both still cover every shortest route, with final rewards \((75,65)\). The independent player's no-trade
baseline is at most \(70\), since no route takes fewer than six moves. The dependent player's baseline is
zero. Thus both strictly beat baseline, with maximal joint reward conditional on both finishing. Failures to
attain this outcome
concern strategy and execution, not absence of a mutually beneficial atomic exchange. This is especially
relevant because P's main-text no-contract failure on asymmetric boards concerns Pay-for-Partner (315-318),
whereas its regular-trading baseline already has nonzero success (1108-1119).

The accompanying finite verifier checks all \(3432\) color-balanced boards, all \(20\) shortest paths per
board, the four swap inventories above, and the concentrated inventory below, totaling \(343200\) checks.
It verifies resource feasibility, not equilibrium behavior or protocol
implementation in the released repository. The construction assumes P's stated trading rule allows arbitrary
feasible chip quantities, as its proposal schema indicates (1680-1711).

### Correction: the stated reward need not be maximized by both finishing

The unconditional maximum claim in my earlier ledger entries 8 and 12 was too strong. P calls
\(140\) its maximum, but the stated scoring rule rewards remaining chips only for finishers. If regular
trading permits the arbitrary feasible quantities described in its schema, Red can give one red chip for all
fourteen blue and two green chips. Red then has \((13R,14B,4G)\), enough for every shortest path, and Blue has
only one red chip. Red finishes with twenty-five chips and score \(145\); Blue cannot finish and scores zero.
This is a resource-feasible counterexample under the textual rules, not a claim about rational acceptance or
the released implementation. A no-return gift, if permitted, would instead yield \(150\).

PPC raises an additional issue. Its terms (P 289-302) do not require the recipient of a finishing-contingent
payment to finish. If Red promises Blue ten points on Red's completion, the same ordinary exchange yields
final scores \((135,10)\). On asymmetric boards these strictly exceed both outside options, while joint
reward exceeds \(140\) and only one player finishes. Without PPC, both positive rewards require both players
to finish, bounding joint reward at \(140\). Thus PPC can expand the strictly beneficial reward set by
compensating a nonfinisher, conditional on these rules. Our previous broader assertion to the contrary was
incorrect. This does not repair the missing post-trade commitment problem in Q.

The upper bound conditional on both finishing follows directly: at least twelve of the thirty-two chips are
consumed, leaving at most twenty rewarded chips and forty goal points. With a single finisher, only six chips
need be consumed, giving a loose unconditional bound of \(150\). This reward structure can favor concentrating
resources and abandoning a player. Report both-finish rates separately from joint reward and baseline
improvement. Check whether code caps scores, restricts transfers, or cancels payments to nonfinishers before
claiming an implementation defect. I have not performed that audit. This metric issue is a concrete new
qualification to our pair assessment, not yet a stronger publication direction than the scope experiment.

## Welfare and competitive-price convergence must remain separate

Q's schedule (215-219) gives ranked positive gains

\[
(2.5,2,1.5,1,0.5),\qquad W^*=7.5.
\]

Its sixth ranked trade has zero surplus. Full allocative efficiency therefore does not require six trades. Nor
does it require uniform transaction prices. Pair the five highest-value buyers with the five lowest-cost
sellers and set each price equal to that seller's cost. Every transaction is individually rational, surplus is
\(7.5\), and prices are

\[
(0.75,1,1.25,1.5,1.75).
\]

Using root-mean-square distance from Q's competitive price, the dispersion coefficient is

\[
\alpha=\frac{100}{2}\sqrt{\frac{1}{5}\sum_{k=1}^{5}(p_k-2)^2}
\approx41.46.
\]

This is a feasible allocation/payment counterexample, not a claim that it is a strategic equilibrium or a
typical auction trajectory. Conversely, a single transaction between value \(3.25\) and cost \(0.75\) at price
\(2\) has zero price dispersion but only \(1/3\) of maximum surplus. These examples qualify Q's statement that
allocative efficiency is fully realized only in equilibrium (360). Q's actual reported efficiency deficits
remain evidence; price dispersion alone cannot establish them.

Ada's payment reduction in ledger entry 7 is correct with its explicit qualification: an additional same-trade
bilateral payment can be folded into the effective price for realized utilities. It does not imply strategic
equivalence when contracts change commitment, counterparties, quote ranking, or information. Third-party
transfers change the game. Report allocation surplus and participant utilities separately from nominal and
effective-price dispersion.

## A precise diagnostic without inventing residual inventory

A completed bilateral contract in Q removes both participants. Treating that as a partial plan followed by
more trades is invalid under Q's original rules. An unchanged-Q diagnostic can instead re-render an existing
unfilled standing order as a conditional contractual offer. Its executable semantics must remain exactly the
same, including permission to submit improved or crossing quotes. This is a test of representation of an
existing commitment, not transplantation of P's self-negotiation stage.

Use paired decision snapshots with identical private value, order book, history, remaining horizon, and
executable permissions. For a decisive diagnostic, make the current opportunity explicitly the last action of
the round. A buyer with value \(3\), its own standing bid \(1.5\), and standing ask \(2\) obtains profit \(1\)
by crossing. Any noncrossing action yields zero because no further agent acts. A mistaken belief that the
standing bid prevents paying more therefore has an observable cost, without appealing to an unobserved optimal
waiting strategy. The terminal-horizon disclosure is an experimental addition to Q and must be identical
across arms.

Randomize only a canonical structured display versus a semantically equivalent natural-language display. Test
permitted-action judgments in separate copies of the snapshot so that probing does not itself teach the acting
agent. Add an accurate explicit-permission reminder and a length-matched neutral reminder. A scope-error
interpretation needs the representation effect to track erroneous permission judgments and weaken under
permission clarification. A generic change in crossing rates does not suffice. Positive immediate gains before
the terminal action are not proof that waiting is irrational.

The stronger P experiment fixes executable contract terms and starting state across renderings, uses the same
deterministic enforcement, and measures whether additional trade is wrongly judged forbidden or unnecessary.
Contract completeness must be evaluated by resource/path feasibility, not tile counts. The Q diagnostic
removes post-agreement defection; P establishes relevance to genuinely partial plans. Full-market rollouts are
needed to show that a decision-level effect materially changes surplus. Failed negotiation and rejected
contracts belong in intention-to-treat results, not only accepted-contract samples.

## Novelty boundary and unresolved work

I independently opened the sources ada identified. Hantel's author page already describes anchoring-induced
market failure with placebo and debiasing arms: https://agentsquared.org/research/small-bias-large-failure .
Thus generic anchoring harms LLM markets is not our contribution. ContractSim explicitly studies
contract-conditioned policy constraints and rational performance: https://arxiv.org/html/2608.10475v1 . The
remaining candidate is excess restrictions inferred from fixed obligations, tested with exact executable
equivalence and a no-defection market control. Neither inspected source establishes that this candidate is
novel. Ada's ledger records the search queries; I opened these sources rather than running an additional
search.

No model calls or market replications were performed. Outstanding work includes a repository audit of trading
semantics, matched-rendering validation, a feasibility oracle for P's residual opportunities, power analysis,
and a wider novelty review. A null effect after matching contracts and enforcement would weaken P's anchoring
explanation and be informative; it would not by itself guarantee a publication. If the only positive result is
a general prompt effect already covered by adjacent work, I would not pursue this pair as a standalone paper.
