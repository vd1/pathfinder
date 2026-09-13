# Contracts can misdescribe an agent's remaining freedom

Ada's assessment of Q, *Competitive Market Behavior of LLMs*, and P, *Commitment To Cooperation With
Self-Negotiated Contracts*.

## Judgment and changed question

The abstract-level proposal, adding P's contracts to Q to cure inefficient convergence, does not yet identify
a useful economic mechanism. I replace it with a narrower, falsifiable question:

**With executable obligations held fixed, does contractual language cause agents to infer restrictions on
profitable actions that remain permitted, and does that error reduce realized surplus?**

This is a plausible publication direction, not a result established by these papers. P supplies a suggestive
failure under incomplete contracts; Q supplies a competitive environment where trade execution is already
enforced and price, allocation, and decision delay can be separated. The useful contribution would be causal
evidence about mistaken contract scope across these different environments. Merely finding that wording
changes trading, or that contracts sometimes help, would be too weak.

## What the papers actually support

Q's Trading Mechanism says that a crossing bid causes a transaction to execute "immediately" at the standing
ask and "both parties exit the round" (`inputs/Q.tex:250-260`). Each trader has a single unit each round
(`Q:241-244`). There is no discretionary delivery decision after acceptance. P's Pay-for-Partner mode
deliberately introduces just such a decision: agreements are nonbinding and the provider can refuse coverage
when it is needed (`inputs/P.tex:199-203`). This is a real institutional difference, not an implementation
inconvenience.

P also bundles several interventions. Programmatic Trading Contracts specify automatic tile-level chip
transfers, with an inventory condition and a zero-score penalty for inability to fulfill (`P:267-277`).
Natural Language Trading Contracts retain the dialogue and have a judge interpret it at each move
(`P:280-286`). Programmatic Points Contracts add terminal transfers contingent on finishing (`P:289-302`).
Negotiation, representation, interpretation, action obligations, and payoff instruments therefore need
separate accounting.

The strongest empirical connection is negative. On mutually dependent boards in the regular-trading mode, P
reports normalized joint reward of \(0.64\) with NLTC versus \(0.93\) without a contract (`P:1381`). Comparing
NLTC with PTC, it reports similar mean contract-covered moves, \(2.58\) and \(2.60\), but trade volumes of
\(1.95\) and \(3.28\) (`P:1383-1385`). Agents declining trade refer to contracts more often under NLTC
(`P:1387`). The main Pay-for-Partner results show a related pattern (`P:421`). These are distinct modes and
their numerical results must not be pooled.

Q reports small quote improvements and reluctance to cross profitable spreads, particularly for GPT Large
(`Q:367-384`). It explicitly cautions that reasoning-text associations do not establish the decision mechanism
(`Q:435-442`). P's statement that natural-language contracts are "causing the models to trade less" (`P:1385`)
is stronger than the isolation achieved by the reported comparisons.

Similar mean executed coverage does not fix contract quality: different tiles, paths, inventories, and timing
can leave different residual needs. Executed coverage is itself an outcome of the intervention. P's judge
audit counts errors among approved moves (`P:1424`); it cannot bound false negatives among rejected moves.
This leaves interpretation errors, negotiated terms, context length, and actor behavior entangled. A
controlled intervention is necessary before naming a common cause.

## Economic boundaries established from the supplied rules

### A terminal payment can be only a net price

Consider a single atomic buyer-seller trade. Let value be \(v\), cost \(c\), exchange price \(p\), and net
buyer-to-seller side payment \(d\), paid only if these same parties trade. With quasilinear utility, no
financing constraint, and no other obligations,

\[
u_B=v-p-d,
\qquad u_S=p+d-c.
\]

The effective price \(p_{\mathrm{eff}}=p+d\) reproduces the allocation and both realized payoffs.
Consequently,

\[
u_B+u_S=v-c.
\]

This is an outcome equivalence, not a general equivalence of auction games. Pair-specific transfers can
reorder effective quotes. Early commitments can change available actions or reveal information. Transfers
contingent on a partner's trade with someone else produce payoff links across traders. None of these changes
is captured by merely renaming a price, and none should be called a pure repair of settlement credibility.

PPC adds terminal-point transfers to P, but regular chip trading already redistributes eventual reward in
increments of \(5\). It would be inaccurate to say P has no means of compensating another player without PPC.
What PPC adds is a different contingent transfer instrument. As the correction below shows, this can expand
the set of strictly mutually beneficial reward outcomes if transfers can compensate nonfinishers.

### P permits optimal joint reward conditional on both finishing without contracts

Emmy supplied a constructive check, which I verified against `P:190-194` and `P:227-232`. Initially exchange
five red chips for five blue chips. Each player then holds nine of its original color, five of the other
color, and two green chips. A Manhattan shortest path has six moves, at most five non-green tiles before the
green goal. Both paths are affordable. Each player retains ten chips and receives \(70\), so the joint reward
is \(140\), P's stated maximum. This is a maximum conditional on both players finishing, not an
unconditional bound under the written trading rules.

Emmy then supplied a stronger asymmetric-board construction, which also checks directly: exchange five red
chips for six blue chips. Red holds nine red, six blue, and two green chips; Blue holds five red, eight blue,
and two green chips. Both can take any shortest route. Final rewards are \((75,65)\), strictly above Red's
independent baseline of at most \(70\) and Blue's baseline of \(0\), while still totaling \(140\). See
`emmy/boundaries.md` and `emmy/verify_bounds.py` for the partner's exhaustive verification. This is a useful
uniform ordinary-trading baseline for P, requiring no board-specific negotiation of the transfer.

These constructions prove feasible outcomes maximizing joint reward conditional on both finishing, including
a strict improvement over both no-interaction outside options on asymmetric boards. They do not prove
incentive compatibility, stable bargaining equilibrium, or that an LLM will choose the exchange and follow a
shortest route.

**Correction after ledger entries 17-18.** My earlier note wrongly treated the completion-conditioned bound as
unconditional. Emmy identified the following counterexample, which I independently checked against the reward
formula (`P:227-232`), contract payment rules (`P:291-300`), and trade schema (`P:1680-1711`). Before moving,
Red gives one red chip for Blue's fourteen blue and two green chips. The inventories become

\[
I_R=(13R,14B,4G),\qquad I_B=(1R,0B,0G).
\]

Red can afford any shortest path and finishes with twenty-five chips, scoring \(145\); Blue cannot finish and
scores zero. This exceeds the stated \(140\) benchmark even under ordinary trading as raw resource
feasibility. It does not strictly benefit Blue and would therefore fail P's stated selfish cooperation
criterion. It is not evidence of observed agent behavior.

There is a useful exact distinction. Without point transfers, every nonfinisher has reward zero and every
baseline is nonnegative. Strict improvement over both baselines therefore requires both to finish. At least
twelve of the initial thirty-two chips are consumed, so

\[
R\leq 2(20)+5(32-12)=140.
\]

The five-for-six swap attains this bound on asymmetric boards. With PPC, if a receiver need not finish to
receive points, Red can first commit ten points contingent on Red finishing and then perform the concentrated
exchange. Final rewards become \((135,10)\), strictly above asymmetric baselines \((b_R,0)\) with
\(b_R\leq70\). Thus PPC can expand the strictly mutually beneficial reward set past joint reward \(140\).
This does not Pareto-dominate \((75,65)\): Blue is worse off relative to that alternative. The new outcome
maximizes neither equality nor number of finishers.

The mechanism is compensation for noncompletion. When both finish, the second finish adds twenty points but
requires at least six chips worth thirty points if held by the first finisher. Transferring all chips to a
single finisher would give the upper bound \(150\); whether that exact bound is attainable depends on whether
one-sided gifts are legal. The nonempty exchange above suffices to refute the unconditional \(140\) claim.
For that exchange, normalized joint reward is \(145/140=29/28>1\). Joint reward, completion, inequality, and
baseline improvement therefore measure distinct properties, even before LLM behavior enters the analysis.

These are conditional statements about the written mechanism. I attempted to inspect the [P
repository](https://anonymous.4open.science/r/colored_trails-70A4), but the browser could not open it and its
[API endpoint](https://anonymous.4open.science/api/repo/colored_trails-70A4/) returned `not_connected`.
Unverified implementation details include transfers to nonfinishers, any restrictions on chip quantities,
scoring order, and termination after one player finishes. P's common system prompt says a nonfinisher gets
zero total points (`P:1617-1620`), which also needs reconciliation with PPC's transfer rule. A prompt preference
to finish is not by itself an executable restriction on the reward-feasible set.

Consequently, my earlier dismissal of the abstract as describing observed behavior only was too strong.
Ordinary trading already permits strict mutual gains and the both-finish optimum, but PPC may alter the
reward frontier through compensation for a different completion outcome. This is a benchmark audit finding,
not a demonstrated explanation of P's measured contract gains. It does not repair Q's already automatic
settlement. The scope experiment remains the main cross-paper candidate, with separate reporting of these
outcome metrics now essential.

### Welfare and price convergence must remain separate

Q's symmetric reservation schedule has optimal ranked gains

\[
2.5,\;2,\;1.5,\;1,\;0.5,\;0,
\qquad W^*=7.5.
\]

Thus five positive-gain trades already attain full welfare; the sixth trade at the reported equilibrium is
marginal and contributes zero. The same efficient allocation can clear at heterogeneous individually
acceptable prices. Conversely, observing a price of \(2\) in a small number of trades says little about the
unrealized gains. This confirms Emmy's separate price/welfare objection. Report physical surplus, individual
payoffs, prices, and volume separately.

For a completed Q trajectory let \(W\) be realized surplus and \(R^*\) the maximal additional surplus
available by optimally matching the remaining buyers and sellers. Then

\[
W^*-W
=\underbrace{W^*-(W+R^*)}_{\text{loss that remaining traders cannot repair}}
+\underbrace{R^*}_{\text{unrealized gains among remaining traders}}.
\]

Both terms are nonnegative because realized trades plus an optimal matching of remaining traders form a
feasible matching of the original market. The decomposition is evaluator accounting; the agents must not
receive private values from its calculation. It distinguishes harm from earlier allocation choices from gains
still left among active traders. It does not infer the agent's causal reasoning or guarantee that profitable
local trades were individually optimal earlier.

## A concrete experiment, with the original scope preserved where possible

### Fixed semantics before free negotiation

Start with an audited bank of states and feasible obligations, rather than letting each display condition
negotiate different contracts. Freeze the states before treatment assignment. In P use incomplete tile
contracts that leave a demonstrably useful ordinary trade available. Ensure the trade will not consume
resources needed to meet a later contractual obligation. First use constructed cases with exact
reachable-state checks; then use independently sampled negotiated contracts for robustness.

Use the same deterministic enforcement function in both display arms. Show either a structured representation
or controlled prose that denotes exactly the same obligations. The full negotiation history, public
information, active contract terms, available actions, and model budget stay identical. A deterministic
renderer and an exhaustive check over the small relevant action/state domain should verify denotation. Do not
use P's runtime judge in the primary experiment: that would reintroduce the interpretation confound. A later
judge arm can attribute any remaining difference to enforcement.

This estimates the effect of the active display after a common history. It is deliberately not a replication
of P's entire JSON-versus-dialogue pipeline. Randomizing only after agreement conditions on a fixed
pre-treatment accepted-contract population, so agreement rates are outside this estimand. Any later end-to-end
negotiation study must include negotiation failures in its results.

In Q, render the *existing* executable standing orders as ordinary order records or as conditional
obligations. Preserve prices, acceptance conditions, replacement/expiry rules, histories, and the original
action interface. Add no negotiation, rewards, promises, compulsory crossing, or new execution service. Verify
the exact order lifecycle in a pinned code version before writing the renderer. The paper alone does not
specify every lifecycle detail.

This is a test of contractual representation of an existing institution. It is not P's partial-contract
treatment moved intact into Q. Emmy correctly observes that a Q agent exits after its single trade, so
post-execution residual trading by that same agent does not exist. The Q contrast concerns adaptation before
execution. A multi-unit extension would make P-like residual trading possible, but would change the
environment and is not necessary for this first claim.

### Distinguish scope mistakes from rational waiting

Ordinary Q snapshots cannot establish that declining positive current profit is irrational: waiting can
improve an agent's payoff. Include separate terminal-opportunity probes in which the agent is explicitly told
that this is its final chance and no later action will execute a trade. For a buyer facing standing ask
\(a<v\), profitable crossing gives

\[
g=v-a>0,
\]

whereas any noncrossing action gives zero in this probe. Its decision regret is \(g\) when it fails to cross,
and zero when it crosses. Use symmetric seller cases. The deadline disclosure is a diagnostic modification,
applied identically to both display arms; do not claim the original Q experiment supplied this information.

On separate cloned contexts ask agents to classify whether specified actions are allowed under the displayed
obligations. Do not append these questions before the actual trading choice, since they could themselves train
attention to contract scope. A representation effect on trading alone is compatible with numeric anchoring,
complexity, or attention differences. A higher false-prohibition rate provides more specific evidence.

P's reported explanations concern not needing further trade, which need not mean believing trade is forbidden.
On separate clones, also test whether the agent mistakenly judges its contract sufficient for completion.
Keep permission errors and plan-sufficiency errors separate. A result confined to the latter would require
reframing the mechanism as mistaken completeness of a plan; it would not establish the narrower prohibition
claim posed here.

Cross the display with an explicit permission clarification logically entailed by the existing rules, such as
stating that an unfilled quote does not forbid an otherwise admissible new quote. Compare against an
equal-budget generic rule reminder and use several paraphrases. Selective rescue of false prohibitions and
terminal regret would support scope overgeneralization, although it would not make internal causal mediation
certain.

In P, use received trade offers and verified continuations to distinguish an erroneous prohibition from a real
inventory conflict or a bad trade. Do not score a refusal as an error simply because joint reward could
increase. Individual incentives and remaining obligations must be checked.

### Market consequences and stopping conditions

After the state probes, run repeated complete markets with representation assigned at the market level.
Primary outcomes are Q's realized surplus and its residual-gains decomposition; in P use joint reward
alongside individual reward and contractual feasibility. Price dispersion and volume are secondary. Report
terminal-regret probes separately from open-horizon trading behavior.

Cluster uncertainty by market run or board/contract instance, not by individual quote. Use the same models in
both environments, balance roles, retain failures, and budget tokens and simulator opportunities equally. A
pilot should estimate variance and set a sample size for a prespecified practically meaningful effect. No
numerical power or required run count can be justified from the aggregate tables alone.

Do not assume matching configuration seeds creates paired Q trajectories. The current [Q repository
README](https://github.com/jswistak/competitive-market-simulation) says mechanism scheduling is unseeded and
its experiment seed controls only zero-intelligence trader randomness. A paired experiment needs explicit
scheduling coupling that preserves each arm's uniform selection law despite different active-agent sets;
otherwise use independent randomized clusters. Pin the version before implementation.

A convincing positive result requires fixed semantics, display-dependent false prohibitions, corresponding
dominated decisions in terminal probes, selective rescue, and a meaningful surplus effect in full interaction.
If only the actor-free judge arm differs, the explanation is interpretation. If only a full-transcript arm
differs, the supported explanation may be context burden. If action choices change without prohibition errors,
describe framing sensitivity rather than contract scope. If effects disappear under controls, or occur in P
alone, report the limited result and do not claim a general cure for Q.

## Prior work and unresolved novelty

I searched the following queries:

- `LLM agents contracts anchoring residual trading contract representation economic efficiency`
- `LLM double auction semantic invariance framing contracts market efficiency`

[Hantel's author summary](https://agentsquared.org/research/small-bias-large-failure) already describes price
anchors that suppress trading in markets of LLM agents, with placebo and debiasing conditions. Generic
anchoring-induced market failure is therefore not the proposed novelty. I inspected the summary, not the full
linked paper.

[Sajja et al., Evaluating Rational Contracting in Natural Language](https://arxiv.org/html/2608.10475v1),
especially Sections 2 and 4, formalizes contracts as constraints on policies and evaluates
contract-conditioned behavior against rational baselines. The proposed advance would be a controlled test of
*extra restrictions inferred from an equivalent representation*, with an already enforced market as a
comparison, rather than introducing contract-constrained rationality itself.

These searches do not establish novelty. The closest controlled semantic-equivalence literature still needs a
deeper check. No LLM experiment has been run here, and no numerical treatment effect is claimed. Feasibility
remains plausible because both environments expose concrete mechanisms, but matched rendering, contract
auditing, code-version verification, and the causal probes require real work. The best current outcome is a
sharply identified research question and reasons to reject the simple transplant interpretation.
