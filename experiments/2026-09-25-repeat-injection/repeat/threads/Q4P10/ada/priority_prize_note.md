# A resource-conserving reward rule for job choice

## Connection and scope

Q permits action- and state-dependent multi-agent reward schedules (Q, lines 1508–1525) and uses
coupled rewards to change strategic behavior (Q, lines 1794–1920). Its peer-scoring construction can
use arbitrarily large rewards and an off-path reward of negative infinity (Q, lines 1661–1702). P
instead makes energy an actual survival resource, charges for generated tokens, grades answers
automatically, and divides a single job prize among successful agents (P, lines 147–169 and
199–225). The question here is whether a coupled payout can improve the *job-choice* incentives in P
without creating or destroying energy.

The result below is a one-round result for active agents who choose a job or idle. Conditional on
each job choice, an agent's answer policy, success distribution, and expected token cost are fixed.
There are no donations or sabotage, and agents maximize expected own round energy. A planner knows
the joint outcome law and can announce a target profile and a payout rule before choices. These are
assumptions for the result, not claims established by P.

## The collision wedge

Let two agents consider job \(j\), with prize \(R_j\), success indicators \(S_1,S_2\), marginal
probabilities \(p_1,p_2\), and joint success probability \(q=\Pr(S_1=S_2=1)\). P's split rule pays a
total of \(R_j\) whenever at least one succeeds. Its expected total payout is

\[
R_j\Pr(S_1=1\text{ or }S_2=1)=R_j(p_1+p_2-q).
\]

Agent 2's expected personal payout is \(R_j(p_2-q/2)\), whereas its marginal contribution to the
job's expected total payout is \(R_j(p_2-q)\). The private excess is exactly \(R_jq/2\). No
independence assumption is needed. If agent 2 could instead take an empty job \(k\), with expected
prize \(R_kp_{2k}\), a privately attractive but socially harmful collision occurs whenever

\[
R_j(p_2-q)<R_kp_{2k}<R_j(p_2-q/2),
\]

assuming the two job choices have the same expected token cost. For a numerical illustration,
\(R_j=800\), \(p_1=p_2=1/2\), independent successes, and an empty job with expected payout \(250\)
give a social marginal payout of \(200\) and a private colliding payout of \(300\). This example is
constructed; it is not an estimate from P. The same formula also shows why some collisions can be
socially useful: if the alternative job's expected payout is below \(R_j(p_2-q)\), a second attempt
raises expected group energy.

## Priority prize construction

Let \(a^\star\) maximize expected total one-round energy over all job-or-idle profiles. For every
job, mark the agents assigned to it under \(a^\star\) as *incumbents*. Set a fixed priority order
that places every incumbent before every visitor. After answers are graded, give the job's entire
prize \(R_j\) to its highest-priority successful solver, or pay zero if no one succeeds. This
changes only the division of P's prize. For each realized outcome, the total job payout is exactly
\(R_j\mathbf 1\{\text{someone succeeds}\}\), as under P's split rule.

**Claim.** Under the stated one-round assumptions, \(a^\star\) is a Nash equilibrium of job-or-idle
choice under the priority prize rule. This allows \(a^\star\) itself to contain collisions.

**Proof.** Hold other agents' choices at \(a^\star_{-i}\). If agent \(i\) is assigned to job \(j\),
removing it reduces expected group payout on \(j\) by

\[
m_{ij}=R_j\Pr(S_{ij}=1,\text{every other incumbent on }j\text{ fails}).
\]

Its own expected priority prize on \(j\) is at least \(m_{ij}\): it wins when it alone succeeds, and
may also win when lower-priority incumbents succeed. If it is assigned idle, both quantities are
zero. If agent \(i\) deviates to a different job \(k\), it is a visitor below all of \(k\)'s
incumbents. Its new expected prize is exactly

\[
m_{ik}=R_k\Pr(S_{ik}=1,\text{every incumbent on }k\text{ fails}),
\]

which is precisely the increase in expected group payout on \(k\). This includes empty jobs. A
deviation to idle gives a new prize of zero. The change in own expected token and idle costs equals
the change in group costs because costs are borne by the choosing agent and other agents' outcome
laws and costs are fixed. Therefore, for every unilateral deviation,

\[
\Delta\mathbb E[\text{own energy}]
\leq \Delta\mathbb E[\text{group energy}]\leq 0.
\]

The last inequality follows from the global optimality of \(a^\star\). Hence no agent benefits by
deviating. The argument allows arbitrary correlation among success indicators. Relative to P's
original split payout, Q's reward adjustment for agent \(i\) can be written as its priority payout
minus its split payout. Across agents these adjustments sum to zero for every realized outcome, and
each agent's adjustment is bounded in magnitude by the job prize. \(\square\)

## What would make this a paper

The theorem gives a budget-balanced, finite analogue of Q's action-coupled rewards for P's
job-choice stage. The empirical question is whether the rule improves *net total energy* and
survival compared with P's split-prize discussion and no-discussion conditions, and how often agents
follow an assigned profile under actual model behavior. The experiment should randomize the payout
rule while holding the available jobs, agent set, assignment information, and discussion or token
budget fixed. It should record every agent's chosen job, correctness, token cost, assigned priority,
and energy path. Replay or fresh trials are needed to estimate counterfactual success and
job-specific costs; P's aggregate collision counts alone cannot identify the welfare change. P
reports higher collision counts without discussion (lines 619–627), but that condition also removes
a charged model-call phase (lines 569–572), changes survival and donations, and alters job
difficulty choice. The current tables do not settle the net-energy question.

Q explicitly identifies dynamic mechanisms as a future direction (Q, lines 2450–2452). P's
repeated rounds and deactivation rule make that extension concrete: characterize when the
one-round priority equilibrium survives continuation values, or construct and test the smallest
counterexample. This is the main unresolved theory step before claiming a broader mechanism
result for P's full environment.

Emmy's ledger entry 12 gives a simple boundary example. Two agents each start with \(15\) energy,
each spend \(10\) on the same job, both succeed, and the job pays \(20\). Splitting leaves
balances \((15,15)\); priority leaves \((25,5)\). If both later face a required call costing
\(10\) with no immediate reward, splitting leaves both active with \((5,5)\), whereas the
priority loser deactivates. Total payout in the first round was identical, yet the set of
agents able to work later differs.

The mechanism does not elicit private success probabilities or guarantee that an LLM follows an
expected-energy best response. Its proof also does not cover strategic answer effort: when a target
job has multiple incumbents, a high-priority agent can privately value increasing its own success
even in cases where another agent would already secure the group prize. Nonlinear value of survival,
donations, learning across rounds, and model-call errors can likewise change incentives. A useful
negative result or boundary would identify when these effects defeat priority assignment under
finite energy. No prior-work search was run, so the note makes no novelty claim beyond the
comparison of Q and P.
