# Q--P synthesis: robustness to the wrong target

## Bottom line

The abstract-level connection is directionally useful but overstated. Q does not show that an LMM referee makes urgency-biased pairwise judgments. It studies LLMs acting as traders under incentives and a finite horizon, and its trace result is restricted to one model. P uses an external LMM referee, supplies two images per ordered comparison, and requests structured output. Transferring Q's particular urgency mechanism to P without testing it would conflate actor behavior with evaluator behavior.

The publishable question I would pursue is narrower:

> Does repeated rank aggregation reduce MARS-RA's errors under active-set churn, or does it concentrate a context-dependent LMM preference into a confidently wrong credit signal?

This changes the scan's question. The key issue is not whether LLM judgments are generically noisy. It is whether P's repeated-query remedy addresses the kind of structured, regime-dependent error for which Q provides an experimental warning and diagnostic template.

## Evidence from Q

Q observes that market efficiency can fail because a stable behavioral pattern is amplified by the institution. GPT Large agents repeatedly make minimal improvements and fail to transact before the round ends, producing only (2.2\text{--}3.8) trades and efficiency of (0.36\text{--}0.67) (Q, lines 360--363). This is not merely independent response noise.

Q also reports model- and role-conditioned behavior. Gemini Large crosses spreads near \(\$0.50\), GPT Large waits until almost zero, and GPT Small lies between them; GPT Small buyers and sellers behave differently despite a symmetric market design (Q, lines 371--375). Opening offers anchor later decisions even when the opposite side is not mechanically constrained by the first offer (Q, lines 398--403). These findings motivate looking for conditional preference shifts rather than reporting a pooled accuracy alone.

Q's reasoning analysis separates incremental and crossing phases. Urgency and execution terms rise in the crossing phase while optimization and strategic terms fall (Q, lines 406--441). Q explicitly says this is suggestive, covers only Gemini Large, does not establish what causes the switch, and may not faithfully reveal the decision computation. Thus it offers a diagnostic design, not evidence that P's comparator has the same mechanism.

## The opening in P

P claims that rank aggregation tolerates comparison noise and dynamic participation (P, lines 208--215). Its theorem assumes that, at each time \(t\), the LMM follows a Bradley--Terry comparator with a stable latent vector \(\mathbf{c}_t^*\), so repeated comparisons estimate that vector with error decreasing as \(O(K^{-1/2})\) (P, lines 361--376). The appendix concentration step requires centered comparison errors, \(\mathbb{E}[y_k]=P_{i_kj_k}^*\), and states that strong convexity scales with \(K\) under uniform pair sampling (P, lines 687--744).

The result therefore guarantees recovery of the LMM's latent preference under its model, not recovery of true contribution. P acknowledges this distinction when its Shapley statement assumes \(\mathbf{c}_t^*=\mathbf{v}_t^*\) and says it does not claim practical Shapley recovery (P, lines 383--389). Repeating a systematically biased comparison can shrink variance around the wrong target.

P's empirical evidence does not isolate that failure mode. It reports pooled agreement with dense reward labels, from about \(0.43\) to \(0.72\) across models, and finds that more queries improve downstream success (P, lines 1049--1074). It identifies low-information views as a common error case, but does not report error conditional on coalition entry or exit, active-set size, remaining battery, task phase, or time to timeout. The benchmark induces churn by action-depleted batteries and random respawn (P, lines 397 and 427), yet there is no fixed-versus-churning or churn-intensity ablation in the paper.

There is also a P-specific risk after comparison. P applies softmax to scores over the current active set and uses differences of that vector as shaping rewards (P, lines 331--349). If an entrant with score \(c_j\) joins while an incumbent's score \(c_i\) stays fixed, its normalized potential changes from

\[
\psi_i=\frac{e^{c_i}}{Z}
\quad\text{to}\quad
\psi_i^+=\frac{e^{c_i}}{Z+e^{c_j}}<\psi_i.
\]

Thus membership can create a normalization jump even with an oracle comparator. This is a testable optimization risk, not a demonstrated policy bias or violation of PBRS: if roster membership is part of the state and the required stationary, fixed-space conditions hold, the potential differences can still telescope despite an abrupt jump. True marginal contribution may also change with coalition membership, and ordinary discounted potential shaping already introduces a term when \(\gamma<1\). P limits its policy-invariance claim to stationary transitions in its limitations (P, lines 642--650). A matched counterfactual must hold incumbent scores and physical state fixed, subtract the ordinary discount component, and compare against a fixed-reference potential. The relevant outcomes are shaping variance, sample efficiency, and downstream success; any claim of changed optimal policy additionally requires a proof that open participation violates the PBRS conditions or direct experimental evidence.

## Concrete study

Start with the deployed MARS-RA interface. P gives the referee each ordered pair's egocentric images, a textual description of the task and rules, image-to-agent identity mappings, and a contribution prompt (P, lines 285--300). It does not say that the prompt supplies churn events, battery levels, deadlines, or active-set metadata explicitly. The primary audit must therefore stratify unmodified MARS-RA judgments by information actually available to the referee: naturally observable proximity to an entry or exit, active-set size only if inferable from the task context or images, battery or phase cues visible in the images, role, visibility, and image order. Adding explicit transition metadata would test susceptibility to an augmented interface, not a failure of deployed MARS-RA, so it belongs in a secondary mechanism experiment.

Use P's dense rewards as an operational external label, not established Shapley ground truth, and evaluate comparisons in matched strata around an active-set transition. For ordered pair \((i,j)\), define signed label \(z_{ijt}\in\{-1,0,1\}\), LMM judgment \(y_{ijt}^{(k)}\), and signed distance \(\tau_t\) to the nearest entry or exit. Estimate

\[
\Pr\!\left(y_{ijt}^{(k)}=z_{ijt}\right)
= f(\tau_t,\text{visible phase cues},\text{role},\text{visibility},\text{order},\text{model}).
\]

The decisive experiment first compares three error processes with the same pooled accuracy:

1. actual LMM judgments;
2. independently flipped ground-truth judgments;
3. structured flips matched to the observed transition, role, and visibility strata.

For each process, vary repeated queries \(K\) and measure pairwise accuracy, calibration, three-cycle rate, held-out Bradley--Terry negative log likelihood, score error against dense-reward contribution, and final policy success. The main estimand is the error floor

\[
B(K)=\mathbb{E}\!\left[\lVert\widehat{\mathbf c}_{t,K}-\mathbf v_t^*\rVert_2\right].
\]

Under centered Bradley--Terry noise, \(B(K)\) should decline approximately as \(K^{-1/2}\). Under a stable context bias \(\boldsymbol\delta_t\), aggregation instead approaches \(\mathbf c_t^*=\mathbf v_t^*+\boldsymbol\delta_t\), so

\[
\lim_{K\to\infty} B(K) > 0.
\]

A stronger negative result is possible: additional queries may increase confidence and shaping magnitude without improving alignment to \(\mathbf v_t^*\). A useful intervention would then stratify or calibrate the comparator at transition boundaries, abstain when observations are uninformative, or diversify prompts/models rather than repeat an identical query. Only after this observational audit should a matched prompt intervention add or remove explicit entry, exit, battery, or deadline metadata while holding the images fixed. That arm tests whether transition context itself induces rank flips, but it cannot by itself establish an error in P's deployed comparator.

As a secondary arm, cross oracle versus LMM comparisons with active-set softmax versus a coalition-invariant reference scale. Oracle plus active-set softmax isolates normalization shock. LMM plus fixed-reference scaling isolates comparator context bias. Their combination measures interaction. Comparator misspecification remains the primary theoretical gap because P's convergence result directly assumes centered Bradley--Terry observations. The normalization arm tests a separate optimization mechanism and should not be presented as an invariance failure without further proof.

Where reasoning traces are available, reproduce Q's lexical or semantic phase comparison between correct and incorrect judgments and between transition-near and transition-far strata. This is secondary evidence only. It should not be required for the core result because P's production comparator may not expose faithful traces.

## Publication threshold and limitations

The study becomes pair-specific and potentially publishable if structured errors interact with P's distinctive open-team mechanism: churn produces a nonvanishing error floor, repeated queries fail or hurt near transitions, and a churn-aware intervention restores performance. A roster-coupled normalization pulse that changes optimization variance or sample efficiency would be an additional P-specific result. If errors are explained entirely by visual information, normalization is harmless, and repeated queries behave similarly in static and churning settings, the pair yields only a generic LLM-as-judge robustness check.

Unresolved points are whether churn-relevant cues are visible in the actual referee inputs, whether P's code exposes per-query judgments and dense reward labels at every transition, whether repeated API calls are independent enough for the stated concentration intuition, whether a contribution ground truth based on instantaneous dense reward is itself valid near delayed cooperative effects, and whether active-set normalization affects the relevant potential-shaping invariance result in the Open Dec-POMDP. No external literature search was used in this assessment.
