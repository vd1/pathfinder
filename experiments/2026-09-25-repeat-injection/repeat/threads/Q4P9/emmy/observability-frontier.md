# Bounded incentives under coarse contract signals

## Question and source connection

Can a contract that pays only on a partner's completion induce costly coverage of a particular tile? This
sharpens the pair question to a local implementability test. Q requires obedience to recommendations under
the actual reward schedule ([Q.tex](../inputs/Q.tex), lines 1550–1605) and observes that rewards can
distinguish only what the evaluator identifies (lines 917–947). Its mechanism class permits unrestricted
rewards (lines 1510–1550). P instead supplies a finite game with one-chip coverage costs and three
restricted contract forms ([P.tex](../inputs/P.tex), lines 187–204 and 248–305).

## Signal and budget bound

Fix a decision history and two feasible actions: honor, indexed by \(1\), and refuse, indexed by \(0\). Hold
subsequent behavior fixed by a stated continuation policy. Suppose honoring reduces the giver's expected
score before any contract bonus by \(c>0\). Let \(E\) be the signal on which a bonus may depend, with
conditional laws \(\mu_1\) and \(\mu_0\). Consider all nonnegative bonus schedules \(t(E)\in[0,B]\). The
maximum contract-induced advantage of honoring is

\[
\sup_{0\leq t\leq B}\left(\mathbb E_{\mu_1}[t]-\mathbb E_{\mu_0}[t]\right)
=B\,\mathrm{TV}(\mu_1,\mu_0).
\]

For a finite signal, put \(t(e)=B\) where \(\mu_1(e)>\mu_0(e)\) and \(t(e)=0\) elsewhere. Its incentive
difference is \(B\) times the sum of positive probability differences, which equals total variation. No
other bounded schedule can do better because each term with a positive difference contributes at most \(B\)
times that difference. The same argument uses the positive set of the signed measure for a general
measurable signal. Thus \(c\leq B\,\mathrm{TV}(\mu_1,\mu_0)\) is necessary for weak obedience. It is
sufficient for this local binary choice if every such bonus schedule is permitted and all other continuation
payoffs have already been included in \(c\). If \(\mu_1=\mu_0\), no signal-based reward changes this
decision, regardless of its size.

If an executor sees a garbled signal \(F\) obtained from \(E\) by the same stochastic kernel under either
action, then \(\mathrm{TV}(\mathcal L(F\mid1),\mathcal L(F\mid0))\leq\mathrm{TV}(\mu_1,\mu_0)\). This
follows because every bounded bonus on \(F\) induces a bounded expected bonus on \(E\). The bound formalizes
the interaction of Q's evaluator precision with P's limited incentives. It does not say that a
natural-language judge is such a garbling without a fixed contract and a measured conditional error model.

## Exact specialization to P's completion bonus

P's Programmatic Points Contract allows the receiver \(j\) to promise the giver \(i\) a transfer
\(x\in[0,20]\) if \(j\) finishes ([P.tex](../inputs/P.tex), lines 288–303). Suppose \(i\) finishes
regardless of this choice, has an available chip, and spending it changes no other payoff. A remaining chip
is worth \(5\) points to \(i\) (lines 187–194 and 222–230). Let \(p_1\) and \(p_0\) be \(i\)'s completion
probabilities for \(j\) after honor and refusal, under the same continuation policy. Then

\[
U_i(1)-U_i(0)=x(p_1-p_0)-5.
\]

Hence this particular contract induces weak honor exactly when \(x(p_1-p_0)\geq5\); strict honor needs a
strict inequality. Its cap makes honor impossible through this incentive alone when \(p_1-p_0<1/4\). If
\(p_1=p_0\), the bonus is behaviorally irrelevant to this move even though the receiver might benefit from
having a chip saved. The general total-variation bound is only a necessary screen here: PPC may pay on
completion, not on an arbitrary subset of signal outcomes.

P reports bottleneck defection falling from \(0.30\) without contracts to \(0.21\) with points contracts
(lines 1010–1026). This is compatible with some pivotal moves meeting the inequality, but does not estimate
\(p_1-p_0\), randomize \(x\), or identify a causal threshold. Programmatic Trading Contracts execute
accepted tile clauses automatically if the giver has a chip and penalize insufficient inventory (lines
261–278). They change the execution rule, so the bonus bound does not rank their outcomes. Their ex-ante
acceptance incentives require separate analysis.

## Current asymmetric boards as a feasibility control

Ada's exhaustive [board oracle](../ada/asymmetric_oracle.py) enumerates the \(3{,}432\) balanced boards in P's
generation rule ([P.tex](../inputs/P.tex), lines 1515–1540). I independently ran it and checked all simple
routes. Of the \(396\) boards with Red independent and Blue dependent, \(314\) have a shortest Blue route
requiring \(k=1\) Red chip and \(82\) require \(k=2\). No longer route reduces the foreign-chip requirement.
The specific \(40\) asymmetric boards sampled by P are therefore covered if they follow the stated rule.

In P's regular trading interface (lines 1680–1722), trade \(k\) Red chips for \(k+1\) Blue chips before
movement. Each player can then take a six-move route with its own inventory. Red and Blue finish with
\(11\) and \(9\) chips, respectively, and score \((75,65)\). These scores strictly exceed their no-interaction
baselines \((70,0)\) and sum to P's maximum joint score of \(140\) (lines 222–242). P reports mean
both-beat-baseline of \(0.20\) for no-contract regular trading on asymmetric boards (lines 1040–1124).
The oracle establishes physical and accounting feasibility, not that the exchange is a bargaining
equilibrium or that agents will find and execute it. It also shows that P's \(20\)-point cap is not the
obvious obstruction on these boards' simple completion paths. Low completion pivotality or larger boards
would be needed to expose a binding cap in the local points-contract analysis.

## Discriminating study

Select histories at a promised coverage decision with verified inventory. Fix the board, players, history,
and a declared continuation policy. In a replay intervention, hold all contract terms except \(x\) fixed,
assign \(x\) across the predicted cutoff when feasible, and record honor, completion, and both scores. This
tests the local execution choice; a separate ex-ante treatment is needed to study whether agents would
accept those bonuses and reach those histories naturally. Estimate \(p_1-p_0\) for each treatment if the
bonus changes continuation behavior. The primary test is whether honor responds to the predicted marginal
value \(x(p_1-p_0)\), especially at histories where the cap makes the inequality impossible. Compare a
separately accepted tile-level contract at the same histories to test the value of automatic execution,
while measuring contract acceptance as its own outcome. A paired display-by-executor experiment in
[contract-representation-note.md](contract-representation-note.md) addresses the different question of why
P's two tile-contract formats diverge.

The local bound is a mathematical consequence of stated assumptions, not a new equilibrium theorem for P's
full sequential game. The strongest publication direction is a boardwise frontier that starts with the
feasibility oracle, checks contract acceptance and sequential obedience under P's actual instruments, then
tests where agents fall short. The papers alone do not establish that frontier or its behavioral explanation.
