# Q and P: Deadline-Conditioned Credit Assignment

## Best publication line

The useful connection is narrower than generic LLM-as-judge unreliability. P claims that rank aggregation is robust to noisy LMM comparisons and naturally accommodates changes in the active agent set. Q suggests a failure mode that rank aggregation does not address: the model's decision rule can drift with urgency. P implements dynamic participation through battery depletion, removal, and delayed re-entry, and each egocentric image includes an energy icon (P, lines 397 and 427). Battery state can therefore be inferable to the comparator. The prompt does not clearly expose the full active set, however, so membership-dependent comparator drift cannot be presumed.

The sharpened question is:

> Do frozen-state context interventions reveal structured LMM contribution bias that persists as comparison count grows, and does P's active-set credit transform independently create consequential reward impulses at membership boundaries?

This changes the scan's question. The target is not whether MARS-RA survives generic noisy labels. The immediate test is whether controlled order, identity, horizon, or coalition cues change judgments while task evidence is fixed. Membership-boundary artifacts are a separate mechanism until an experiment shows that membership information is present or inferable and that the two effects interact.

## Evidence from Q

Q reports incomplete market convergence and lower allocative efficiency than the human benchmark (Q, lines 135-174 and 340-360). Its individual-level mechanism is reluctance to cross a spread, with small repeated price improvements causing rounds to terminate before trades occur (Q, lines 354-360).

For Gemini Large, Q compares reasoning traces during incremental moves and spread-crossing moves. Urgency and execution terms rise in the crossing phase, while strategy and optimization terms fall (Q, lines 409-438). The authors interpret this as increased weight on completion later in a round, but explicitly warn that the analysis is correlational, covers one model, and reasoning traces may not reveal the causal computation (Q, lines 409-442). Therefore Q supplies a motivated diagnostic and hypothesis, not established general evidence about LMM judges.

## Evidence from P

P fits a Bradley-Terry model at each step to pairwise LMM preferences among currently active agents and softmax-normalizes the inferred scores for potential-based shaping (P, lines 286-350). Its robustness proposition assumes a connected comparison graph, a stable latent preference vector, and Bradley-Terry observations. It proves convergence of the estimator to the LMM's latent preference as comparisons K increase (P, lines 356-376). It does not prove that this preference equals true contribution. The later Shapley interpretation makes that equality conditional on a rational comparator whose latent preference is already determined by true Shapley values (P, lines 383-389).

P's empirical accuracy measure uses agreement with per-agent dense reward, and reports that greater comparator accuracy and more queries improve average success (P, lines 546-552). This does not isolate state-dependent bias around entry, exit, or deadlines. P itself says comparator accuracy remains important (P, lines 642-646).

## Specific dynamic-agent problem

P initializes a fixed n-by-n comparison matrix but defines the inferred score and softmax potential only over the active set, then forms γψ(s_{t+1},t+1) - ψ(s_t,t) even though I^{t+1} may differ from I^t (P, lines 285-350). The text does not specify how active-set vectors are aligned across membership changes. A fixed-population embedding can make the subtraction well-defined, but active-set softmax still renormalizes every survivor's potential when a peer enters or exits, even if the survivor's inferred contribution is unchanged. This can create a shaping impulse caused solely by coalition composition. It is a credit-validity and learning-variance concern, not by itself a failure of PBRS policy invariance when the potential is well-defined and Markovian.

This observation is independent of Q. A combined contribution first establishes each mechanism separately, then tests whether the structural impulse and Q-style context sensitivity reinforce each other near exits.

## Minimal decisive experiment

Stage 1 freezes visual trajectories and reference contribution while varying only image order, identity mapping, and randomized horizon or coalition cues. Cross these conditions with query count K. This is the gating experiment: estimate whether a context-conditioned bias floor remains as repeated queries reduce sampling variance.

Stage 2 replays naturally occurring removal and respawn transitions through current active-set softmax, fixed-population masked potentials, and an entry/exit-invariant centered potential. Measure boundary reward impulses, reward variance, and downstream learning. This stage does not require the comparator to observe membership.

Across stage 1, measure label-flip rate, agreement with dense reward or controlled synthetic labels, reversal consistency, Bradley-Terry residuals, three-cycle rate, held-out negative log likelihood, and any available reasoning-language shift. Only after both stages establish effects should a factorial experiment test their interaction near exits.

The publication threshold is a context-conditioned bias floor as K grows, a membership-boundary shaping effect, a downstream learning consequence, and improvement from a context-aware, uncertainty-weighted, or entry/exit-invariant remedy. An interaction would strengthen the paper but is not assumed.

## Assumptions, possible failures, and scope

- Q's urgency evidence may not generalize from Gemini Large trading behavior to multimodal contribution judging. The matched-cue intervention tests this rather than presuming it.
- Battery metadata may be visually entangled with genuine contribution. Counterfactual overlays or prompt-only horizon cues are needed to hold task evidence fixed.
- Dense per-agent reward is an operational reference, not necessarily true long-horizon causal contribution. Results should be reported against both dense reward and controlled synthetic scenarios with known contributions.
- P may implement fixed-size alignment despite not specifying it for the active-set score vectors. Code inspection could resolve that ambiguity, but softmax composition dependence would remain unless the potential is constructed to be entry/exit invariant.
- A negative urgency result would still leave a useful technical result if active-set normalization generates measurable shaping artifacts. If neither effect changes learned behavior, the pair likely does not support a full paper beyond a robustness note.
