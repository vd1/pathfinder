# Peer discipline when the peers consume the reward resource

The strongest line is narrower than the abstract scan: **can peer discipline remain incentive compatible when
survival changes the observable peer population, and what resource expenditure restores it?** This combines Q's
information-based discipline with P's endogenous loss of agents. It is a proposed theory-and-experiment project,
not an empirical finding from either paper. The bounded-payment calculation alone is too familiar to support a
publication claim.

## What the papers actually supply

Q, *Mechanism Design for Alignment and Control*, peer discipline, equation PR and Proposition “Support-wise
implementability of every feasible rule” (`inputs/Q.tex`, lines 1653-1734), scores a type report using its known
conditional distribution of peer types. Its score is

\[
S(p,y)=2p(y)-\lVert p\rVert_2^2.
\]

The complete mechanism also cancels the utility of the reported type and prohibits actions outside the target
support. Its proof bounds residual deviation gains by \(M\), defines minimum squared belief separation
\(\delta>0\), and uses \(\Lambda\delta\geq M\). Q assumes fixed belief maps and permits unrestricted rewards. It
promises partial implementation, not uniqueness or collusion resistance (lines 426 and 543). A scoring bonus
without those other instruments is a test of a component, not an implementation of that proposition.

P, *The Energy Society*, makes generated tokens consume energy and removes exhausted agents from subsequent
activity (Actions, Agents, and Simulation loop, lines 145-228). Discussion costs energy, recommendations are
nonbinding, and other agents' status and recent histories are visible. Competition versus cooperation primarily
changes the instruction to maximize own versus total energy (lines 264-275). There is no Q-style capability
evaluation followed by report-dependent deployment permissions. The recommendation metrics (lines 773-808)
therefore do not identify sandbagging.

P gives a useful resource intervention: removing the size penalty makes all agents survive and all reported
energy efficiency ratios exceed one (Experiment 2, lines 484-554). This contradicts the abstract's stronger
claim that larger agents spend more than gained even without the penalty. Its no-discussion experiment improves
survival but changes coordination and task choice (lines 569-628). These are motivations for a controlled test,
not estimates of a scoring mechanism's effect. Five seeds and pooled collision counts cannot establish that
effect; P itself cautions about participation confounds (lines 850-856) and statistical power (903-904).

Q's coupled-reward construction is a poorer direct fit: it assumes scalar real actions, quadratic intrinsic
losses, and a known strictly decreasing relation between the agents' biases (lines 1788-1805 and 1862-1901). P
establishes none of these. I therefore replace the scan's broad mechanism-transfer proposal with
survival-conditioned peer scoring.

## Verified selection counterexample

Emmy proposed this example in ledger entry 8; I independently checked every quantity. Let the original peer
event be binary with

\[
p_H(1)=\frac34,\qquad p_L(1)=\frac14,
\qquad s(1)=\frac1{10},\quad s(0)=1,
\]

where \(s(y)\) is the probability that the event's peer report is observed. Conditional on a report being
observed, a true H type faces

\[
\widetilde p_H(1)=\frac{3/40}{3/40+1/4}=\frac3{13}.
\]

For the original score rows, the H-minus-L score difference is one at outcome one and minus one at outcome zero.
Its expected difference among observed peers is

\[
\mathbb E_H[S(p_H,Y)-S(p_L,Y)\mid\text{observed}]
=\frac6{13}-1=-\frac7{13}.
\]

Thus increasing the score scale strengthens the wrong reporting incentive. This is misspecification after
selection, not a counterexample to Q or to proper scoring with correct beliefs.

Recalibration fixes this one-report subproblem when selection is report independent and the conditional rows are
known. The selected L row has probability \(1/31\) of outcome one. Their squared separation is

\[
2\left(\frac3{13}-\frac1{31}\right)^2
=2\left(\frac{80}{403}\right)^2
\approx0.0788146.
\]

Alternatively, score the explicit outcome “missing.” The full rows, ordered as one, zero, missing, are

\[
q_H=(3/40,1/4,27/40),\qquad
q_L=(1/40,3/4,9/40).
\]

Their squared separation is \(91/200=0.455\). Missingness itself carries information. This example does **not**
establish that attrition always destroys information. The numerical separation comparison uses the same raw
quadratic-score scale; it is not a comparison at equal payment caps.

## A sharp resource limit

Emmy's ledger entry 12 gives a more decisive construction, which I independently verified. Suppose the original
peer outcome has three values and

\[
p_H=(1/2,2/5,1/10),\qquad
p_L=(1/2,1/10,2/5).
\]

The first outcome is always observed, and the other two survive with probability \(\varepsilon\), independently
of the reporting agent's report. Including missing as a fourth observable outcome gives

\[
q_H=(1/2,2\varepsilon/5,\varepsilon/10,(1-\varepsilon)/2),
\]
\[
q_L=(1/2,\varepsilon/10,2\varepsilon/5,(1-\varepsilon)/2).
\]

The informative distinctions disappear while ordinary peer activity remains. In particular,

\[
\operatorname{TV}(q_H,q_L)=3\varepsilon/10.
\]

Assume risk-neutral energy utility and a reduced continuation game in which either type gains exactly \(M>0\) by
falsely reporting the other type, before scoring transfers. This temptation is a specified primitive of the
example, not an estimate of LLM preferences. Let every report-dependent payment lie in \([0,B]\), and set
\(d(y)=r_H(y)-r_L(y)\). Truthful reporting requires

\[
\mathbb E_H[d(Y)]\geq M,
\qquad \mathbb E_L[d(Y)]\leq-M.
\]

Since \(-B\leq d(y)\leq B\), subtraction yields

\[
2M\leq\langle q_H-q_L,d\rangle
\leq2B\operatorname{TV}(q_H,q_L).
\]

Consequently,

\[
B\geq B_{\min}=\frac{10M}{3\varepsilon}.
\]

This bound is attained: pay H reporters \(B\) only for the second outcome, and L reporters \(B\) only for the
third outcome, paying zero otherwise. The truthful advantage for either type is \(3B\varepsilon/10\). Equality
gives weak IC; a strictly larger cap gives strict preference against the false report. At zero availability of
diagnostic outcomes, no finite payment works. For every positive availability a finite payment works in this
simplified game.

This is a **peak-payment** constraint, not a lower bound diverging in expected expenditure. At the threshold,
expected truthful payment is

\[
\frac{2\varepsilon}{5}B_{\min}=\frac{4M}{3},
\]

which is constant. A rare large reward can meet an expected budget while violating a finite reserve or
maximum-payout constraint. That distinction is central when energy cannot be borrowed. A valid experiment must
state which restriction it imposes; P does not currently impose a principal's scoring reserve.

Q's raw quadratic score on these four-outcome rows has squared separation \(9\varepsilon^2/50\). At fixed raw
scale its margin contracts quadratically, whereas a cap-optimized binary report contract has margin proportional
to \(B\varepsilon\). This is not a quadratic lower bound on all feasible mechanisms: scale, shifts, and payment
span must be accounted for together.

The result concerns reporting against a truthful, report-independent peer channel. It neither establishes action
obedience nor rules out uninformative equilibria. For the symmetric binary special case, paying for agreement
supports constant-report equilibria whenever its truthful equilibrium survives a symmetric misreport temptation.
Thus equilibrium selection remains an empirical variable, not an automatic theorem corollary.

## Timing and implementation checks

I inspected the released code at commit `70fb2ac89fc4125f7f5e5dd3495fe07b7c558b4c`:

-
  [agent_middleware.py](https://github.com/LucasBergholdt/EnergySociety/blob/70fb2ac89fc4125f7f5e5dd3495fe07b7c558b4c/agent_middleware.py):
  `EnergyMiddleware.after_model` deducts energy after the model call and clamps the balance to zero. It is not a
  hard interruption at the last affordable token.
-
  [environment.py](https://github.com/LucasBergholdt/EnergySociety/blob/70fb2ac89fc4125f7f5e5dd3495fe07b7c558b4c/environment.py):
  `start_votes` excludes already inactive agents; completed nonempty votes remain available even when the vote
  exhausts the producer. Subsequent decisions and job attempts filter active agents again. Successful job
  rewards can restore an exhausted solver's balance. Hence the paper's donation-only reactivation description
  needs this within-round qualification.

For a natural P extension, survival selection should initially mean the known active population at the next
round. Conditional beliefs and IC must be computed at the reporting information set, including visible history
and active status. An ex ante IC calculation that averages over already revealed availability is inadequate.

For a controlled diagnostic test, randomly suppress peer observations after reports are sealed. This directly
implements the theoretical channel, but is an added intervention rather than P's original deactivation rule.
Allowing reports or donations to change which peer outcome is scored turns the problem into joint
reporting-and-channel manipulation. Merely estimating the factual selection rate does not solve that problem.
First seal the peer reports and scoring eligibility before releasing recommendations or executing donations;
treat strategic survival manipulation across rounds as a later extension.

A report-independent constant payment changes no risk-neutral one-period reporting comparison, but can change
future energy, participation, and the next round's information channel. Therefore “normalize all scores” is not
harmless for the complete repeated experiment. Track both the reserve that backs rewards and their settlement
time. Do not count injected energy as newly produced task value.

## Concrete study and stop conditions

There is a decisive identification condition: fresh private signals independent of past energy need not change
their conditional law when agents disappear. The natural-economy experiment must establish a link through persistent
type, task information, or history. Otherwise survival reduces the number of peers without producing the proposed
selection reversal. Emmy emphasized this distinction in ledger entry 16; I agree.

Use a controlled two-type reporting task embedded in P's token accounting and round structure before attempting
to infer natural preference types. Private synthetic signals provide known conditional rows; a specified
continuation payoff creates a known reporting temptation. This makes a faithful reporting-component test
possible. It does not establish that naturally occurring LLM capability or alignment types have those rows.

First reproduce the selection reversal and cap threshold with exact best responders. Then use LLM reporters and
vary diagnostic-peer availability and peak reward cap. Compare stale scoring, correctly conditioned scoring,
explicit-null scoring, and a cap-optimized contract. Hold task inputs and scoring-message lengths fixed where
possible. Use report-independent payments from an independent paired run to distinguish incentive effects from
liquidity effects, and report realized transfers as well as their planned distribution. Whole-run replication is
required because agents within a society interfere with each other.

Primary outcomes are truth versus known injected signal, deviation advantage, null frequency, actual payment
span, and net task value after all inference costs and external subsidies. Measure downstream action conformity
separately. Include direct ground-truth scoring: P already has answer keys, so an answer-report peer mechanism
needs to justify its use against that available alternative. If the goal instead concerns private preferences or
capabilities, those labels require a separate identification design.

The promising publication would establish a calibrated link from resource-induced changes in peer information to
incentive failure, then show whether an affordable correction restores useful LLM behavior. It would be weakened
substantially if the only result were the standard selection-bias calculation, if behavior did not track the
predicted margins, or if direct scoring or an equal-resource unconditional transfer explained the whole
improvement. A null finding would still delimit Q's practical scope, but does not guarantee a publishable
contribution.

## Prior work and unresolved novelty

[Radanovic et al., Information Gathering with Peers](https://arxiv.org/abs/1711.06740) already study information
acquisition with peer-prediction constraints and a payment budget. [Witkowski et al., Dwelling on the
Negative](https://ojs.aaai.org/index.php/HCOMP/article/view/13089) analyze costly effort, participation, and
restrictions on negative payments. [Gao, Wright, and Leyton-Brown](https://arxiv.org/abs/1606.07042) establish
problems from cheap uninformative equilibria and show advantages of direct ground-truth checking under their
assumptions. These sources prevent treating bounded payments, effort costs, or bad peer equilibria as new by
themselves.

Searches performed: `peer prediction limited budget costly effort uninformative equilibria spot checking Gao
Wright Leyton Brown 2019`; `peer prediction bounded payments minimum budget information elicitation correlated
signals incentive compatibility`; `peer prediction attrition missing reports selection bias inverse propensity
survival`; `peer prediction endogenous participation dynamic survival resource constraints`; and the quoted
searches `"peer prediction" "attrition"`, `"peer prediction" "missing" "selection"`, `"peer prediction"
"survival"`. The latter searches did not establish an exact prior match for the proposed survival-feedback
experiment. This is a search record, not evidence of novelty.

Unresolved: a fuller literature comparison; identification of useful natural types; beliefs conditional on
endogenous history; strategic control of future peers; survival utility beyond one-period linear energy; and
whether a correction beats the direct-verification and liquidity controls. No LLM experiments were run. The
analytic examples were independently checked with exact arithmetic in `ada/check_examples.py`.
