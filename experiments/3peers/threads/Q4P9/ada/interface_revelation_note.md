# Contract Compilation as a Capability Intervention

## Assessment

The abstract-level connection should be rejected. Q's one-sided imitation condition concerns hard evidence about types: a capable type may withhold a certificate, while an incapable type cannot fabricate one (Q, lines 299--303). In P's natural-language treatment, the contracting agents do not choose an interpretation after observing whether performance is convenient. An external Qwen judge interprets the retained negotiation and automatically executes covered transfers (P, lines 280--286). P reports only (3) errors among (1{,}155) approved moves, all false positives (P, lines 1422--1426). This is not evidence that agents counterfeit commitments.

There is a narrower and stronger connection. Q treats an agent's execution capability (A[t]) and information experiment \(\pi[t]\) as fixed primitives (Q, lines 276--297). Its revelation proof replaces an arbitrary mechanism output with the contingent action plan induced by equilibrium play. The key step says that the indirect agent can copy every direct deviation (Q, lines 406--423; multi-agent version, lines 1618--1642). Thus the representation used to convey an extensionally fixed plan has no independent effect under Q's unrestricted strategy model.

P suggests that this closure-under-copying condition may fail for LLM agents. On mutually dependent boards, PTC and NLTC produce about the same contractual coverage, approximately (2.60) tiles per game, but both players finish in (79\%\) of PTC games and (46\%\) of NLTC games. NLTC elicits fewer supplemental proposals, (1.4) rather than (3.0), and agents refusing a needed trade cite their insufficient contract in (94\%\) rather than (74\%\) of cases (P, lines 416--421). The proposed interpretation is not failed enforcement but representation-dependent planning: compiling an agreement changes the agent's effective continuation strategy set.

## A theory target

Let (z) denote the interface that represents a recommendation and let \(\Sigma_i(z)\) be the continuation strategies that agent (i) can execute through that interface. Q implicitly sets \(\Sigma_i(z)=\Sigma_i\) for every (z). Its revelation construction needs simulation closure: for every equilibrium continuation \(\alpha_i(x_i,y_i,s_i)\) of an indirect mechanism and every admissible direct deviation (d_i), the corresponding composed continuation must belong to \(\Sigma_i(z)\). If compilation from (z) to a direct plan destroys that closure, the equality of indirect and direct outcome sets can fail even when payoffs, physical actions, evidence, and enforcement are unchanged.

A useful result would characterize an interface preorder. Write (z'\succeq z) when every strategy executable from (z) can be simulated from (z') without changing the induced distribution of physical actions. Revelation survives within an interface class exactly when the direct interface dominates the indirect interfaces used in the construction. This recasts contract compilation as a capability intervention rather than a stronger commitment device. It also marks the boundary of Q's theorem instead of merely applying its cyclical-monotonicity test to another benchmark.

## Identifying experiment in CT-Bench

P's existing comparison cannot identify this claim because PTC and NLTC do not hold contractual semantics fixed. The PTC judge summarizes dialogue into JSON and asks both agents to accept it, while NLTC retains the full conversation for later interpretation (P, lines 267--304). Similar mean coverage does not establish identical obligations board by board.

The decisive follow-up freezes a negotiated obligation map (c(h,a)), then independently randomizes:

1. agent-facing representation (z\in\{\text{canonical JSON},\text{lossless canonical prose}\});
2. enforcement (e\in\{\text{exact program},\text{LLM judge}\});
3. completeness of the frozen agreement (q\in\{\text{sufficient},\text{deliberately missing one required coverage}\}).

The hidden canonical map supplies ground truth in all cells. Both renderings expose exactly the same fields and contingencies. A full-transcript arm can diagnose context effects, but it is not an isomorphic representation because it supplies extra information. Both agents explicitly accept the same extensional obligations, and prompts, board, model, and turn order are paired. Primary outcomes are supplemental trade proposals and acceptances after contract formation, completion, dominated refusals, and ex-post regret relative to feasible beneficial residual trades. The preregistered interface prediction is

\[
\mathbb{E}[\text{supplemental trades}\mid z=\text{natural language},q=\text{incomplete}]
<
\mathbb{E}[\text{supplemental trades}\mid z=\text{JSON},q=\text{incomplete}],
\]

even under exact programmatic enforcement. An enforcement account instead predicts a primary effect of (e). The rejected counterfeiting account predicts opportunistic disputed-coverage attempts concentrated under judge enforcement. The completeness interaction tests P's specific over-anchoring mechanism: a complete contract should leave little need for supplemental planning.

Use multiple runs per board and model. P uses (n=1) for most cells (P, line 315), so board-paired repeated trials are necessary to separate representation effects from sampling noise. The same design can include heterogeneous model pairs, which P's later analysis shows can have sharply asymmetric promise keeping (P, line 1513).

## Publication claim and limits

The combined paper could establish an interface-aware revelation principle plus a controlled failure test: payoff-equivalent contractual interfaces need not be behaviorally equivalent for LLM agents because representation changes cognitively feasible strategies. Q supplies the exact proof step and fixed-capability abstraction to amend; P supplies an environment, a striking failure signature, and a ready manipulation.

What remains unresolved is whether the matched-semantics effect exists. P's current evidence motivates but does not identify it. Equality of equilibrium outcome sets also does not select a unique LLM outcome, which is why dominated-action and regret measures are important. The theory requires a non-circular restriction on \(\Sigma_i(z)\), such as a resource-bounded program class or an empirically estimated policy class. Without that discipline, “effective capability” simply renames observed behavior and is not a publication-level explanation.
