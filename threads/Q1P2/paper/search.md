# Prior-work search record

Searches were run on 11 September 2026. OpenAlex was used for broad discovery, then the arXiv API and arXiv abstract pages were used to verify metadata. The relevant papers were downloaded and read, with attention to their assumptions, calibration unit, downstream transfer, and stated scope.

## Queries and results

1. OpenAlex: `conformal prediction Hausdorff distance point cloud`

   The leading results concerned conformal geometry in the unrelated mathematical sense, point-cloud compression, completion, and reconstruction. No result used split conformal prediction with a Hausdorff wall-set score or a thresholded wall-distance gate.

2. OpenAlex: `conformal prediction robotic perception abstention geometry`

   The results included a survey of run-time monitoring for robotic perception but no exact Hausdorff-to-wall-gate certificate. The broad query was too noisy to establish novelty.

3. OpenAlex: `split conformal simultaneous point cloud`

   The results were unrelated to conformal prediction. No exact match was found.

4. OpenAlex: `selective perception conformal robotics wall detection`

   The results concerned haptics, soft sensors, semantic mapping, and unrelated perception topics. No exact match was found.

5. arXiv API: `all:"conformal prediction" AND all:robotics`

   This returned *Sample-Efficient Safety Assurances using Conformal Prediction* (arXiv:2109.14082) among other robotics papers. Reading it showed finite-sample conformal calibration of warning systems, explicit exchangeability assumptions, and marginal rather than joint guarantees across test cases. It does not use wall sets, Hausdorff scores, or P's gate.

6. arXiv API: `all:"conformal prediction" AND all:perception`

   This returned *Safe Perception-Based Control under Stochastic Sensor Uncertainty using Conformal Prediction* (arXiv:2304.00194) and *Perceive With Confidence: Statistical Safety Assurances for Navigation with Learning-Based Perception* (arXiv:2403.08185). The first calibrates state-estimation regions and feeds them to a measurement-robust controller. The second calibrates learned object detection and scene completion for safe navigation, including a treatment of planner-induced state shift. Both establish that conformal calibration can be coupled to a downstream robotics mechanism. Neither gives the room-level Hausdorff-to-distance reduction or simultaneous first-wall-gate statement here.

7. arXiv API: `all:"conformal prediction" AND all:Hausdorff`

   The returned papers did not concern robotic wall estimation or the claimed gate transfer. No exact match was found.

8. arXiv API: `all:"selective prediction" AND all:robot perception`

   The results included work on adaptive abstention in autonomous perception but no room-level wall-set calibration or matching hard gate.

9. arXiv API: `all:"Hausdorff" AND all:"conformal prediction"`

   A round-3 rerun returned *Common-Center Geometry and Certified Radial Reconstruction for Energy-Form Full Conformal Regions* (arXiv:2608.24964). Its use of Hausdorff geometry concerns the shape and reconstruction of full conformal prediction regions, not wall-set error, robotic perception, or threshold-gate decisions. It therefore does not publish the result claimed here.

## Effect on the paper

The search rules out a broad novelty claim for conformal calibration in robotics. That pattern is already published. The paper therefore claims only the specific reduction supported by the Q-P ledger: calibrating a room-level Hausdorff score and using the distance-to-set inequality to obtain simultaneous correctness of all non-abstained decisions at P's first wall-distance gate. No exact prior publication of that result was located by these searches. The related-work section says this directly and cites only records whose title, authors, year, URL, and arXiv identifier were verified against the arXiv API and abstract records. Metadata for all five cited arXiv papers was rechecked in round 3.
