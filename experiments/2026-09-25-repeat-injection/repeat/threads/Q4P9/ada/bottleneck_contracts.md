# Completion bonuses and bottleneck coverage in CT-Bench

## Candidate question

When can a terminal, goal-contingent point transfer make a player honor
a promised Pay-for-Partner coverage at a bottleneck? Can the answer predict
which CT-Bench histories need tile-level enforcement? This sharpens the
broad pair question to a restricted mechanism-design problem: P supplies
observable actions, payoffs, and contract forms, while Q supplies the
relevant honesty-and-obedience incentive condition.

## Sources and mapping

P defines a move as consuming a matching chip and a finisher's score as
\(20+5n_i\), where \(n_i\) is remaining inventory
([P.tex](../inputs/P.tex), lines 187–194 and 222–229). Pay-for-Partner
(P4P) promises to cover future moves remain defeasible at execution
(lines 196–204). In Programmatic Points Contracts (PPC), a player can
pledge up to \(20\) points to the other, paid only when the pledging player
reaches the goal (lines 288–303). Programmatic Trading Contracts (PTC)
instead execute specified tile coverage automatically when the giver has
a chip; insufficient inventory gives the giver zero points (lines 261–278).
P identifies goal-adjacent tiles controlled by a player who may already
be secure and reports that PPC reduces bottleneck defection from \(0.30\)
to \(0.21\) (lines 1010–1026).

Q's multi-agent direct mechanism requires a player to prefer the
recommended action to any feasible deviation after accounting for its
own utility and the reward schedule ([Q.tex](../inputs/Q.tex), lines
1550–1605). Q permits arbitrary action-and-state contingent rewards
(lines 1510–1550) and proves a revelation principle for that broad class
(lines 1618–1643). P restricts transfers and observables sharply. Q's
result therefore motivates the incentive calculation below but does not
by itself prove it for P's sequential game. Treat a P4P decision as a
continuation subgame with the present inventories and routes fixed.

## Local incentive calculation

Suppose player \(i\) has already reached the goal or can finish
regardless of this choice. Player \(j\) is about to enter a tile that
\(i\) promised to cover. The promised chip is available, and using it
does not change \(i\)'s own chance of finishing. Assume \(j\) promised
\(x\) PPC points to \(i\) contingent on \(j\)'s goal completion, and
no other transfer changes with this move. Let \(p_1\) and \(p_0\) be
\(i\)'s subjective probabilities that \(j\) finishes after coverage
and after refusal, respectively, using the same continuation assumptions.
Covering changes \(i\)'s expected payoff by

\[
\Delta U_i=x(p_1-p_0)-5.
\]

The \(5\) is the exact terminal cost of one spent chip conditional on
\(i\) finishing. Hence coverage is a weak best response precisely when
\(x(p_1-p_0)\geq5\). If the coverage is certainly pivotal,
\(p_1=1\) and \(p_0=0\), so the threshold is \(x\geq5\).
Strict obedience requires \(x>5\). If \(p_1-p_0<1/4\), the PPC
limit \(x\leq20\) cannot induce coverage even at its maximum. If
\(p_1=p_0\), the completion bonus has no marginal effect on this
decision. A tile-level automatic transfer can execute the coverage in
that case, provided the contract was accepted and the giver retains the
chip. Its ex-ante acceptance still needs its own incentive analysis.

For a simple chain in which \(j\)'s success requires \(k\) otherwise
unrewarded chips from \(i\), refusal of any chip blocks success, and
\(i\)'s own completion is secure, a plan to provide all \(k\) chips
yields incremental payoff \(x-5k\) against immediate refusal. Thus
\(x\geq5k\) is necessary for initial willingness to provide the whole
chain, and sufficient for each later coverage decision in this simple
chain. Under \(x\leq20\), strict willingness is impossible for
\(k\geq4\). This chain claim does not apply when \(j\) can reroute,
reciprocal coverages save \(i\)'s chips, the players renegotiate, or
\(i\)'s own goal is affected.

## Exact asymmetric-board witness

The cap issue is limited on P's present boards. I enumerated all
\(\binom{14}{7}=3432\) balanced boards using P's board rule
([P.tex](../inputs/P.tex), lines 1515–1540) and all simple start-to-goal
paths. The reproducible calculation is in
[asymmetric_oracle.py](asymmetric_oracle.py). There are \(396\) boards
with Red independent and Blue dependent. Each has a six-move Red-only
path and a six-move Blue path requiring \(k=1\) or \(k=2\) red coverages.
The counts are \(314\) and \(82\), respectively. P samples \(40\) such
boards; the text does not identify the sampled boards in machine-readable
form here. Every selected board must nevertheless have one of these two
path patterns if it follows the stated generation rule.

Assume a PPC can be combined with a P4P offer of \(k\) red coverages
and that a one-sided P4P offer is accepted by the game interface. Blue
promises Red \(x=5k+1\) points upon Blue's completion. Both follow
their six-move paths, and Red honors exactly the \(k\) red coverages.
The score accounting is

\[
r_R=70-5k+x=71,\qquad
r_B=70+5k-x=69,\qquad
r_R+r_B=140.
\]

P's asymmetric baselines are \(b_R=70\) and \(b_B=0\), so this
contract gives \(BBB=1\), the maximum joint reward, and strict gains
over each outside option. Red's total chip cost is \(5k<x\); Blue
strictly prefers \(69\) to \(0\). At the chosen route, after any subset
of coverages Red prefers completing the remaining obligations when
refusal would prevent Blue's completion. Off-path rerouting can make a
particular requested coverage merely weakly optimal, and contract
acceptance still depends on the P4P proposal rules. Thus this is an
explicit attainable-path witness under the stated interface assumption,
not a proof that every history has a strict equilibrium.

This changes the interpretation of the \(k\geq4\) budget observation:
it applies to larger or altered boards, while P's current asymmetric
boards have \(k\leq2\) on suitable shortest paths. P reports mean
\(BBB=0.10\) for P4P with PPC, despite \(0.92\) contract acceptance
([P.tex](../inputs/P.tex), lines 712–787). The oracle gap suggests
planning, terms, execution, or strategic reasoning are failing on many
boards; P's aggregate table alone cannot apportion the gap.

### Reciprocal tile-contract witness

There is a simple accounting screen for any chip-coverage mechanism.
Let Red's realized route use \(L_R\) moves, with \(c\) chips paid by
Blue for Red and \(d\) chips paid by Red for Blue. With no other chip
exchanges, Red's terminal score if it finishes is

\[
r_R=20+5(16-L_R+c-d)
=70+5\bigl(c-d-(L_R-6)\bigr).
\]

Therefore Red strictly beats its asymmetric baseline \(70\) only if
\(c-d>L_R-6\). On a shortest route this reduces to \(c>d\):
coverage must flow toward the independent player in net chip count.
P reports that \(49\%\) of asymmetric PTC contracts assign an equal
number of tiles to each player ([P.tex](../inputs/P.tex), lines
418–425). If equal assigned clauses are all executed and no other
coverage occurs, they cannot make Red beat baseline. Assigned counts
alone do not reveal delivered counts, and subsequent P4P agreements
can change the net flow, so the reported \(49\%\) is not a failure
rate estimate. It identifies an exact term-level diagnostic to measure.
P already measures net promised tiles and reports an informational
visibility intervention that raises Red's mean net promised tiles
from \(0.2\) to \(0.45\), with \(p\approx0.15\) (lines 675–696).
The extra diagnostic is to compare promised with *delivered* net
coverage and the route-length adjustment in the inequality above.
P's P4P plus PTC runs attain mean asymmetric \(BBB=0.06\pm0.03\)
despite mean contract acceptance \(0.80\pm0.03\) (lines 799–885).
These are aggregate outcomes from one run per board and model, not
evidence that the score inequality is the particular cause of failure.

The PTC format gives a stronger witness under an explicitly described
interface. Choose one of Blue's six-move paths with \(k\) Red and
\(5-k\) Blue intermediate cells. Both players traverse that same path.
In the PTC JSON, assign each Red cell to Red as giver and Blue as
receiver, and each Blue cell to Blue as giver and Red as receiver.
Transfers occur automatically when the named receiver attempts the
cell, provided the giver retains a matching chip
([P.tex](../inputs/P.tex), lines 261–278). Each player pays for its
own-color cells on its own traversal and covers the same-color cells
on the other's traversal. Each also spends one green chip at the goal.
The resulting score pair is

\[
(r_R,r_B)=(95-10k,45+10k)
=\begin{cases}
(85,55),&k=1,\\
(75,65),&k=2.
\end{cases}
\]

Both score pairs strictly exceed the asymmetric baselines \((70,0)\)
and sum to \(140\). Red uses at most four of its fourteen Red chips;
Blue uses at most eight of its fourteen Blue chips. The oracle script
checks these claims for all \(396\) boards. This is a concrete
contract-and-path feasibility witness with strictly positive gains
for both players relative to noninteraction. It does not establish
that agents negotiate these terms or that following the entire path
is a sequential equilibrium under every off-path continuation.
There is a limited obedience result after acceptance: if the other
player follows the shared route and no further trades occur, each
player's own route minimizes its matching-color chip expenditure.
Any feasible Red route can use at most the \(5-k\) contracted Blue
cells, so among at least five intermediate cells it must pay for at
least \(k\) Red cells. The shared route reaches that lower bound.
Likewise, any feasible Blue route can use at most the \(k\)
contracted Red cells and must pay for at least \(5-k\) Blue cells.
The coverage cost for the other player's fixed route is unchanged
by one's own route choice. This proves best responses within that
restricted route-choice subgame; it does not settle negotiation or
deviations that change the other player's continuation behavior.
Unlike the PPC construction, it uses reciprocal clauses directly
specified by P's PTC format and needs no assumption about unilateral
P4P offers. A no-contract P4P path with the same coverages would have
the same final scores if all promises were honored; P does not state
the full P4P offer syntax, and those promises remain defeasible.

There is also an unconditional witness under P's regular trading
interface, which explicitly allows unequal chip quantities
([P.tex](../inputs/P.tex), lines 1680–1750). Blue gives Red \(k+1\)
blue chips in exchange for \(k\) red chips, then both take their
six-move paths. Red and Blue finish with \(11\) and \(9\) chips,
respectively, yielding \((r_R,r_B)=(75,65)\). Both accept a trade that
strictly improves their baseline payoffs, and after the exchange
each can finish without relying on future coverage. P's mean
no-contract regular-trading \(BBB\) is \(0.20\) (lines 1040–1124).
This establishes physical and simple voluntary-trade feasibility
independently of the one-sided P4P offer assumption. The PPC witness
then asks the harder question of execution-time obedience.

## What P does and does not test

P reports a modest fall in bottleneck defection under PPC, consistent
with some completion bonuses changing local incentives. It does not
vary \(x\) exogenously at otherwise identical bottleneck histories, so
the aggregate fall cannot establish the threshold. Nor does the
observation that PTC improves cooperation isolate incentive compliance
from path planning, contract selection, and automatic enforcement. P
notes that asymmetric boards often give the strong player little
additional payoff despite helping the weak player (lines 398–402),
which motivates a separate analysis of acceptance and gain sharing.

A discriminating follow-up would hold a board, inventory, history,
contracted coverage, and agent pair fixed, then randomize only the
payable bonus across values below and above \(5/(p_1-p_0)\). Compute
pivotality by exhaustive continuation search for deterministic agents,
or estimate it from repeated continuations under a declared policy.
Measure execution-time honor, the receiver's completion, the giver's
final score, and contract acceptance separately. Add an automatically
enforced tile-coverage condition as an enforcement benchmark. A
discontinuity in honor near the predicted threshold, conditional on
physical chip availability, would support an incentive account;
failure to respond despite accurate comprehension would point to
bounded strategic reasoning. Histories with low pivotality test the
predicted failure of completion-only transfers even at the
\(20\)-point cap.

## Limits and publication assessment

The displayed condition is a local necessary-and-sufficient best-response
calculation under explicit assumptions, not a general equilibrium theorem
or a novelty claim. The broader publishable result would characterize
the boardwise set of cooperative paths implementable with P's bounded
terminal transfers and voluntary acceptance, compare it with tile-level
enforcement and immediately executed trades, and test the frontier
with controlled interventions. The reciprocal PTC and regular-trade
witnesses show that strict Pareto improvement and maximum joint score
are reachable on every present asymmetric board. They do not settle
negotiation or dynamic obedience. Those questions require sequential
incentive constraints and repeated runs. Neither paper supplies that
analysis alone. The current pair supports a concrete research program
and a falsifiable prediction, not an established empirical finding
that agents respond to the threshold.
