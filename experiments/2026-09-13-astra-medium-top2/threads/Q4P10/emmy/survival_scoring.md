# Peer discipline when the resource budget changes the peer evidence

Research note by emmy. This note sharpens the initial abstract-level proposal, rather than treating P as an
existing implementation of Q. The candidate publication question is: **Can an energy-funded peer mechanism preserve
informative incentives as its own computation and payments change which peers remain available?**

The finite results below are proved benchmarks, not empirical findings about LLMs or claims of mathematical
novelty. The promising advance is an experimentally identified feedback between resources, peer evidence, and
action quality. Neither supplied paper establishes that feedback. A generic demonstration that peer rewards change
behavior would be insufficient.

## What the papers actually supply

Q explicitly calls rewards “free” and “unbounded” in its introduction (Q.tex, line 267). Its peer mechanism uses a
quadratic score on co-player reports, subtracts reported intrinsic utility, and prohibits off-target actions
(equation PR, lines 1676–1698). The proof uses the positive minimum squared distance between type-conditioned peer
beliefs and chooses a sufficiently large scale (lines 1704–1734). This is partial implementation: the desired
behavior is an equilibrium, without a general guarantee against other equilibria (lines 426 and 543).

P instead makes energy both the operating resource and the prompted objective. Generating tokens costs energy,
agents can become inactive, donations can restore participation, and discussion is omitted when only one agent is
active (P.tex, lines 154–170 and 211–215). Its energy cost is \(C=kTS^{\alpha}\), counting reasoning and output
tokens (lines 300–305). Removing discussion improves survival while changing job allocation and collision counts
(lines 620–630). This makes the cost of elicitation consequential, rather than an external accounting detail.

The fit has limits:

- P's competitive and cooperative treatments change prompt objectives, respectively individual and total energy
  (lines 264–276). They do not implement Q's reward construction.
- P's multiple-choice jobs have automatically checked answers (lines 186–191). Peer evaluation of correctness needs
  a direct-check baseline; it is not required merely to discover answer keys.
- P's self-serving communication measures concern collision recommendations, donation requests, and recommendation
  following (lines 765–806). They do not establish concealed capability or an evaluation-to-permission channel,
  which is central to Q's sandbagging example (Q.tex, lines 990–1015).
- Q's coupled-reward theorem requires real-valued actions, quadratic intrinsic utilities, and a known decreasing
  curve linking biases (lines 1788–1807). P establishes none of these. Replacing P's task economy with that game
  would test a different application.
- P's abstract says large models spend more than they gain even without size-dependent token costs. Experiment 2
  says all agents remain active and all efficiency ratios exceed one (lines 484–556). The body and table support an
  energy-pressure treatment contrast, not universal resource collapse.

## A score can reverse its incentive after survival selection

Fix a reporting agent whose private type is \(t\in\{H,L\}\), and a truthful reference peer outcome \(Z\in\{0,1\}\).
Let the pre-selection belief rows be

\[
p_H(1)=\frac34,\qquad p_L(1)=\frac14.
\]

The Q-style unscaled quadratic score is

\[
S(r,z)=2p_r(z)-\lVert p_r\rVert_2^2.
\]

Suppose a peer report is available with probability \(s(1)=1/10\) after outcome \(1\) and \(s(0)=1\) after outcome
\(0\). This is a reduced-form channel, not a claim about P's current reporting implementation. Conditional on
availability, the type-conditioned beliefs become

\[
\widetilde p_H(1)=\frac{3}{13},\qquad
\widetilde p_L(1)=\frac{1}{31}.
\]

Before selection, type \(H\)'s expected score advantage of reporting \(H\) over \(L\) is \(1/2\). After selection,
a mechanism that still uses the original score rows gives

\[
\mathbb E_H[S(H,Z)-S(L,Z)\mid Z\text{ observed}]
=2\frac{3}{13}-1=-\frac7{13}.
\]

The truthful score is \(11/104\), while the false-report score is \(67/104\). If missing reports receive a
report-independent payment, the unconditional difference is \(-7/40\). Multiplying these scores by a positive scale
makes the wrong incentive stronger. No intrinsic temptation to misreport is needed for this reversal.

This does not contradict proper scoring or Q. The mechanism has used the wrong conditional-belief map. If selection
is known and fixed against deviations, replacing each original row by its survivor-conditioned row restores the
proper-score argument. The conditional squared separation is

\[
\lVert\widetilde p_H-\widetilde p_L\rVert_2^2
=2\left(\frac{80}{403}\right)^2.
\]

Alternatively, include nonresponse as a contractible outcome. Over outcomes \((0,1,\varnothing)\), the correct rows
are

\[
q_H=\left(\frac14,\frac3{40},\frac{27}{40}\right),\qquad
q_L=\left(\frac34,\frac1{40},\frac9{40}\right).
\]

Their squared separation is \(91/200\). In this particular construction nonresponse identifies outcome \(1\),
because outcome \(0\) is always observed. Thus attrition has not erased the latent distinction if nonresponse is
retained. An early interpretation that disappearance necessarily destroys information would have been wrong. Ada
independently verified both the reversal and this qualification in ledger entry 11.

Inverse-probability scoring is another correction when the selection probabilities are known, positive, and
unaffected by the scored agent's deviation:

\[
S^{\mathrm{IPW}}(r,Z)
=\frac{\mathbf 1\{Z\text{ observed}\}}{s(Z)}S(r,Z).
\]

Its expectation recovers the original score. However, rare observations can require large realized payments.
Clipping these payments need not preserve the score identity. Recording nonresponse avoids that particular
inverse-weight construction, but still requires correct beliefs about the enlarged outcome space.

## When correct nonresponse handling is insufficient

Here is a separate construction in which attrition genuinely removes report-relevant information. Let the latent
peer outcome have three possible values, with

\[
p_H=\left(\frac12,\frac25,\frac1{10}\right),\qquad
p_L=\left(\frac12,\frac1{10},\frac25\right).
\]

The respective probabilities of observing these outcomes are \((1,\varepsilon,\varepsilon)\), where
\(0\leq\varepsilon\leq1\). Including nonresponse gives

\[
q_H=\left(\frac12,\frac{2\varepsilon}{5},
\frac{\varepsilon}{10},\frac{1-\varepsilon}{2}\right),\qquad
q_L=\left(\frac12,\frac{\varepsilon}{10},
\frac{2\varepsilon}{5},\frac{1-\varepsilon}{2}\right).
\]

Thus

\[
\operatorname{TV}(q_H,q_L)=\frac{3\varepsilon}{10},\qquad
\lVert q_H-q_L\rVert_2^2=\frac{9\varepsilon^2}{50}.
\]

At \(\varepsilon=0\), the observable laws are identical although the original laws are distinct. Reward scaling
cannot recreate the missing evidence. This identifies the relevant separation as the separation of the
**contractible channel under the current resource regime**, rather than the pre-selection population.

### A finite-payment lower bound and an attaining mechanism

Suppose both types obtain an additional intrinsic utility \(M>0\) from the false report's continuation. Assume
action obedience is enforced separately, utility is linear in the bonus, and bonuses satisfy \(0\leq R(r,y)\leq
B\). The channel law must be fixed under the agent's reporting deviation. Let \(d(y)=R(H,y)-R(L,y)\), so
\(|d(y)|\leq B\). Truthful reporting requires

\[
\mathbb E_{q_H}[d]\geq M,\qquad
\mathbb E_{q_L}[d]\leq-M.
\]

Subtracting and using the definition of total variation yields

\[
2M\leq\sum_y(q_H(y)-q_L(y))d(y)
\leq2B\operatorname{TV}(q_H,q_L).
\]

Consequently \(B\operatorname{TV}(q_H,q_L)\geq M\) is necessary. This is a general necessary condition for the
stated two-type problem, not a general sufficiency theorem for arbitrary channels or utility maps.

For the displayed symmetric construction it is attained: pay \(B\) for report \(H\) when the second outcome occurs,
pay \(B\) for report \(L\) when the third occurs, and pay zero otherwise. Each type's truthful bonus advantage is
\(3B\varepsilon/10\). Therefore the exact minimum peak bonus is

\[
B_{\min}=\frac{10M}{3\varepsilon}\qquad(\varepsilon>0).
\]

Equality gives weak incentive compatibility; strict incentives require a strict inequality. No finite bonus works
at \(\varepsilon=0\). This extends Ada's binary benchmark in ledger entry 4 by making its distinguishing power
depend on availability.

The peak-payment qualification matters. At the threshold, expected truthful payout in this construction is
\(4M/3\), independent of positive \(\varepsilon\). Rare evidence creates a liquidity and worst-case payment problem
even when expected spending stays bounded. Do not conflate a peak payment constraint, an expected treasury
constraint, and total energy consumption. The bound alone proves neither loss of expected-budget feasibility nor
failure of an entire resource economy.

### Quadratic-score scale is not the payment range

The sharp diagnostic-bonus contract can itself be obtained by normalizing Q's quadratic score. For the symmetric
channel above, define the report-independent, outcome-dependent baseline

\[
b(y)=\min_{r\in\{H,L\}}S(q_r,y),\qquad
R(r,y)=\Lambda\bigl[S(q_r,y)-b(y)\bigr].
\]

Because the channel is fixed under reporting deviations, subtracting this baseline leaves each type's expected
report comparisons unchanged. The two belief rows have equal squared norms. Consequently the normalized reward
is zero on the common and missing outcomes, and pays only for the diagnostic outcome matching the report:

\[
B=\frac{3\Lambda\varepsilon}{5},\qquad
\Lambda_{\min}=\frac{50M}{9\varepsilon^2},\qquad
B_{\min}=\frac{10M}{3\varepsilon}.
\]

Thus the quadratic score attains the same sharp peak-payment bound after normalization. Its scale grows as the
inverse squared availability, but its minimum realizable payment range grows only as inverse availability in this
example. A comparison claiming a quadratic-score payment disadvantage from the scale alone would be incorrect.
This normalization preserves reporting incentives under linear utility and a fixed channel; it does not preserve
energy trajectories or settle joint deviations that alter the outcome law.

## Timing, public history, and the proposed test

All channel laws above must be interpreted conditional on information available **when the agent commits its
report**. If active status is already public, it belongs in that conditioning information. One cannot score an
event that is already known as though it were a future random reference outcome. If private signals are freshly
independent of past energy histories, past survival may not bias those signals at all. This is an empirical
identification condition, not something supplied by the survival metaphor.

Ada's code audit found an additional timing constraint: completed discussion votes remain available even if their
generation exhausts energy; exclusion occurs for agents inactive before the discussion. The relevant sources are
[agent_middleware.py][middleware]
and
[environment.py][environment].
I independently checked these files. Thus a natural P extension must analyze selection across rounds or explicitly
add a deadline. Treating every costly completed call as a missing report would misimplement P.

The smallest useful study has a calibrated finite subgame followed by a test in the original task economy:

1. Introduce controlled private signals and a known report-dependent allocation temptation. Use scripted truthful
   reference peers first, sealed reports, a fixed observation channel, an explicit treasury, and enforced
   continuation actions. Vary signal-dependent availability and peak bonus independently. Verify the sign reversal
   and the predicted feasibility boundary with exact best responders before using LLM reporters. This isolates
   reporting incentives; it is not yet a test of full action discipline.
2. Replace scripted peers with LLM agents and measure actual report choices, information retained in reports,
   comprehension failures, and unilateral deviation gains. Log inactive and invalid-response outcomes separately.
   Preserve the same injected signal distribution and prescribed bonus table across models. Introducing free action
   choice adds a separate obedience test.
3. For the P economy, first estimate whether current public history and resource state change the peer evidence
   channel. Compare a frozen belief map, a map conditioned on public history, and a mechanism that includes future
   nonresponse where the timing permits. Freeze the current-round peer assignment and settlement rules before
   reports. Evaluate endogenous donations and peer manipulation separately, because these make the channel itself a
   strategic action.

Payments must come from an explicit common initial resource allocation or a recorded external treasury. Compare
against report-independent transfers with the same resource envelope, a no-scoring communication condition, and
direct ground-truth scoring wherever ground truth is available. Equal expected transfers are not sufficient near
deactivation: timing, recipient, and payout variation can change survival. Use a diagnostic treatment with
protected participation to identify report incentives, then remove that protection to measure the resource
feedback.

The primary outcome should combine useful task output with total inference energy, including scoring and any
additional reporting. Treat action quality, truthful reporting, available-peer information, and survival as
distinct outcomes. Report whole-run outcomes across independently seeded societies. Report collision rates
conditional on the number of active job attempts alongside aggregate collisions; P itself notes the exposure
confound (lines 844–849). P's five seeds are preliminary evidence, not a power calculation for this experiment
(lines 908–913).

## Prior-work check and publication threshold

A limited search found direct predecessors to the simpler parts of this idea:

- Q itself discusses empirical LLM peer scoring at lines 1779–1782, citing
  [Qiu, Carroll, and Allen, 2026](https://arxiv.org/abs/2601.20299). Their paper evaluates and trains LLMs using
  peer prediction, including recovery after malicious fine-tuning with a smaller expert model. Therefore an
  empirical bridge from peer prediction to LLM behavior is already present in Q's own discussion. Our proposed
  distinction must be the resource-dependent evidence channel and its effect on action discipline.
- [Miller, Resnick, and Zeckhauser, 2005](https://www.presnick.people.si.umich.edu/papers/elicit/FinalPrePub.pdf)
  discuss costly effort, participation, budget balance, sequential interaction, and conflicts of interest in peer
  prediction.
- [Witkowski et al., 2013](https://ojs.aaai.org/index.php/HCOMP/article/view/13089) study costly effort,
  heterogeneous quality, participation screening, and restrictions on negative payments.
- [Radanovic et al., 2018](https://arxiv.org/abs/1711.06740) formulate budget-constrained selection of data
  providers with peer-prediction requirements and test their approach in crowd sensing.
- [Gao, Wright, and Leyton-Brown, 2016](https://arxiv.org/abs/1606.07042) show that low-cost common signals support
  uninformative equilibria and that direct ground-truth checking can outperform peer methods under their
  assumptions.

Queries run: `peer prediction missing reports selection bias costly information limited budget scoring rules
participation`; `peer prediction endogenous participation attrition scoring rules budget constraints`;
`"Information Gathering with Peers" budget`; `"peer prediction" "missing" reports selection`; `"peer prediction"
"survival" energy`; `Qiu 2026 truthfulness peer scoring language models expert peer prediction`.
This is a scoped search, not proof of novelty or a comprehensive review.

The viable claim is conditional: **resource-aware peer discipline can require preserving the information channel as
well as financing the transfer, and the Energy Society can measure whether this feedback matters for LLM action
quality.** To support a publication, the study must show a material resource-induced channel change, a correction
or impossibility boundary predicted by the formal model, and a benefit or informative failure relative to
equal-resource and direct-check baselines. If channel shifts are negligible, or direct checking dominates at the
same resources, the broad proposed bridge is not compelling on the evidence currently available.

The counterexamples and bounds are checked in `verify_scoring.py` using exact rational arithmetic. No LLM
experiments or full Energy Society runs have been performed for this note. Endogenous peer selection, nonlinear
value of energy near deactivation, and novelty beyond the cited literature remain unresolved.

[middleware]:
  <https://github.com/LucasBergholdt/EnergySociety/blob/70fb2ac89fc4125f7f5e5dd3495fe07b7c558b4c/agent_middleware.py>

[environment]:
  <https://github.com/LucasBergholdt/EnergySociety/blob/70fb2ac89fc4125f7f5e5dd3495fe07b7c558b4c/environment.py>
