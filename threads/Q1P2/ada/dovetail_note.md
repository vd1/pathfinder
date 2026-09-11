# Robust concept-guided detection from the Q-P pair

## Sharpened question

Can P's top-down, room-constrained door detector retain its speed advantage when the room concept is correct while having a prediction-independent bound when the room concept is wrong?

This sharpens the original broad question from "is there an interesting connection?" to a particular algorithm, bound, and experiment.

## Formal core

Treat the instantiated room and its walls as structural advice. Let A be P's advice-following detector, which searches only wall-constrained regions, and let B be a complete prediction-independent detector over the current observable scene. Assume both computations are preemptible, preserve state between slices, and consume the same divisible resource unit. Let C_A(I, h) be the work A needs to return a valid door under room hypothesis h, with infinity allowed when h excludes the door. Let C_B(I) be B's work; completeness means it is finite on the declared instance class.

Allocate fraction 1 - λ of the resource to A and fraction λ to B, for 0 < λ < 1, until either returns a door that passes the same independent validity check. Then

`C_mix(I, h) ≤ min(C_A(I, h)/(1 - λ), C_B(I)/λ)`.

The proof is the standard time-sharing argument: after total work C_A/(1 - λ), A has received C_A work; after C_B/λ, B has received C_B work. Hence the first completion occurs no later than the smaller threshold. With correct advice and C_A small, the first term is a consistency statement. For arbitrary advice, including C_A = infinity, the second is a prediction-independent robustness statement.

This is not yet a theorem about robot elapsed time. P's intentional motion is serialized by the mission-monitoring agent, and sensing actions can change later observations. For an active version, the paper must either restrict the result to concurrent point-cloud processing or add switching, motion, and state-migration costs. Q explicitly says these are proof obligations.

## Error and evaluation

A useful error is downstream work inflation, not raw room-coordinate error:

`η(I, h) = C_A(I, h) - C_A(I, h⋆)`, truncated below at zero, with infinity when the constrained region omits every valid door.

The bound becomes smooth whenever one can prove `C_A(I, h) ≤ C_A(I, h⋆) + g(η_geom)` for a geometric room-model error. Establishing or falsifying such a stability relation is a substantive part of the project. Mahalanobis innovation is an observable trigger, but it is only a proxy until linked to missed-door work or detection risk.

Experiments should vary the noise and drift ranges already proposed by P, add nonrectangular and partially occluded rooms that induce false accepted concepts, and compare constrained A, global B, and the mixture across λ. Report detection recall and latency, robot motion, CPU/GPU work, false concept permanence, revisions, and downstream topological error. P's current aggregate geometry results in simplified environments do not test this robustness claim.

## Why the pair matters

P supplies the concrete prediction interface, concurrency substrate, active-sensing implementation, and documented failure where incorrect room models become permanent. Q supplies the consistency/robustness contract, costly-query accounting, and the warning that stateful switching and feedback invalidate automatic composition. Neither alone gives this detector or experiment: Q has no robotics instantiation, while P proposes monitoring and revision without a prediction-independent performance bound.

## Main unresolved points

The global detector B must be specified and shown complete under a declared sensor/visibility model. Independent door validation may itself rely on the fallible room concept. Resource divisibility is plausible for point-cloud processing but not for motion. Novelty against prior robust active perception and algorithm-selection work has not been searched in this note.
