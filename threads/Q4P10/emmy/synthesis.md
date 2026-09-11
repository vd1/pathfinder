# Resource-constrained peer discipline in the Energy Society

## Sharpened question

I changed the broad question from whether the papers have a connection to a specific one:

> Can Q's peer-discipline mechanism improve truthful communication and efficient job allocation when rewards must be bounded, budget-balanced, and paid from the same energy stock that keeps agents active?

This is not tested by either paper. Q proves implementation with instruments that P deliberately makes unavailable. P supplies an executable environment in which the consequences of removing those instruments are measurable.

## The bridge

Q assumes correlated private types and a separation condition: distinct types induce distinct beliefs over co-player types (Q, lines 1649-1670). It assigns a quadratic peer score, cancels the reported utility on the target path, and assigns minus infinity off that path (Q, lines 1672-1695). Its proposition implements every feasible rule for sufficiently large score scale Lambda (Q, lines 1697-1699). The proof defines the minimum squared belief separation delta and the maximum gain M from misreporting, then requires Lambda at least M/delta (Q, lines 1704-1734).

P has the ingredients for an empirical version: heterogeneous models, public histories about peers, a costly discussion report before simultaneous final actions, and observable job outcomes (P, lines 188-220). It also finds that competitive agents recommend collisions and solicit donations, evidence that cheap-talk reports can be self-serving (P, lines 870-880). Removing discussion increases collisions (P, lines 850-858), so communication has real allocation value even before incentives are added.

The central mismatch is productive. Q's proof uses minus-infinity punishments, utility cancellation, and rewards that do not enter human welfare. In P, energy is the reasoning budget and survival condition, jobs pay at most 800 energy, and transfers cannot exceed current balances (P, lines 147-176). Since cooperative welfare is total energy (P, lines 264-275), minting peer-score energy would mechanically improve the reported outcome. A valid test therefore needs bounded, budget-balanced peer payments.

## Minimal theoretical result

For Q's quadratic-score construction, let delta be the minimum squared distance between the peer-belief distributions associated with two reports, and let M be the largest intrinsic gain from a supported false report. If the maximum feasible score scale is Lambda-bar, the same argument yields truthfulness only when Lambda-bar times delta is at least M. Equivalently, any environment with Lambda-bar times delta below M lies outside the guarantee of Q's construction.

In Energy Society, Lambda-bar is endogenous. Limited liability caps how much a reporting agent can lose, but budget balance alone does not cap the score scale by that agent's wealth: peers or a common escrow can fund a positive prize. The relevant constraint is the maximum outcome-contingent reward spread under the specified funding rule. If each agent must self-fund escrow, that spread contracts with its current energy; with pooled escrow, it instead depends on group wealth and contribution rules. This gives a dynamic hypothesis absent from both papers: self-funded peer discipline should weaken near deactivation, even if belief separation is unchanged.

This is a bound for Q's proposed construction, not yet an impossibility theorem for every bounded mechanism. A publication should either prove the broader constrained-implementation frontier or state the narrower result precisely.

## Experiment

At discussion time, require each agent to report (1) its recommended allocation and (2) a probability distribution over each peer's final action or job choice. Score forecasts against realized peer actions. Randomize the score scale across runs and compare:

1. no scoring;
2. minted scoring, as a diagnostic upper benchmark only;
3. bounded budget-balanced scoring funded by per-round self-escrow or pooled escrow;
4. the same escrow treatment with score scale normalized by current energy.

Use identical job draws and model assignments. Primary outcomes should be recommendation truthfulness, forecast calibration, compliance with an announced collision-free allocation, collisions, and total endowment-adjusted energy net of token and communication costs. Survival and the distribution of energy are secondary outcomes. Estimate empirical delta from forecast distributions and empirical M from profitable deviations or controlled payoff tables, then test whether behavior changes near the predicted Lambda equals M/delta threshold.

The strongest falsifier is that larger score stakes fail to improve truthfulness or obedience even for solvent agents with clearly separated forecasts. That would challenge the expected-utility and stable-type interpretation needed to transport Q into this LLM setting. If scoring works only when minted but not when budget-balanced, the result identifies resource constraints rather than a failure of peer prediction itself.

## Main cautions

P does not currently elicit beliefs or private types. Its recommendations are public, non-binding action proposals, so existing logs cannot estimate Q's beta maps or test the proposition. Five seeds and prompt-sensitive local models also cannot support a general claim (P, limitations, lines 892 onward). The proposed work is therefore a new preregistered experiment, not a reanalysis presented as verification.

There is also a conceptual confound between model identity, capability, and type. Forecast separation across model identities is not automatically private type separation. A clean design should randomize private signals or private job-competence information within each model, creating known correlated types while holding model identity fixed.
