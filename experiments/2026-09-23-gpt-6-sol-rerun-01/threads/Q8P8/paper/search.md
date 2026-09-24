# Prior-work search for the Q8P8 handover limit

Search date: 23 September 2026. The search targeted the specific claim that a donor wrist frame may fail to specify
an occluded object's pose after in-hand reorientation. Results below describe the returned items, not an exhaustive
novelty determination.

| Query | Returned and read | Effect on paper |
| --- | --- | --- |
| `"DynaMAC" "in-hand" handover wrist object pose` | No exact pairing in the returned results. The results included [Liang et al.](https://arxiv.org/abs/2002.12160) on tracking moving in-hand objects during occlusion. | The paper does not claim that occluded in-hand pose tracking is new. |
| `"handover" "wrist pose" "in-hand rotation" object occlusion` | No direct test of the Q8P8 pairing surfaced. Results included [Wen et al.](https://arxiv.org/abs/2003.03518) on pose estimation for highly occluded objects in adaptive hands and [Liang et al.](https://arxiv.org/abs/2002.12160). | Reinforced the boundary between the information-limit argument and a new estimator. |
| `"One Hand Watches The Other" object pose handover occlusion` | No independent follow-up on P's wrist substitution surfaced. Results again included occluded in-hand pose work. | The paper describes a conditional limit, not a documented failure of P. |
| `robot handover object pose ambiguity wrist frame in-hand manipulation occlusion` | Results included [Handover Control for Human-Robot and Robot-Robot Collaboration](https://pmc.ncbi.nlm.nih.gov/articles/PMC8138472/) and [Liang et al.](https://arxiv.org/abs/2002.12160). | Kept pose-aware handover and pose tracking outside the novelty claim. |
| `"10.1080/01691864.2017.1380535"` | The [publisher landing page](https://www.tandfonline.com/doi/full/10.1080/01691864.2017.1380535) identifies Vezzani, Regoli, Pattacini and Natale's 2017 paper. Its abstract says that estimated in-hand object pose guides the receiving hand. | The main idea of selecting a receiving pose from estimated object pose is already published and is stated as such. |
| `"Vezzani" "1380535" handover` | Returned the same publisher record and abstract. | Confirmed the prior-work classification. |
| `"object pose" "wrist pose" "handover" "in-hand"` | Returned [Grasp Pose Generation for Human-to-Robot Handovers Using Simulation-to-Reality Transfer](https://link.springer.com/chapter/10.1007/978-3-032-03488-5_26), which generates grasp poses in a wrist coordinate system from images. | This is a different handover setting and supplies no measured test of P's substitution with Q's hand. |
| `"DynaMAC" "Aero Hand Open"` | No direct combined study surfaced in the returned results. | No cross-system performance claim was added. |

Bibliographic details in `references.bib` were checked against the Q, P and Liang et al. arXiv abstract pages
linked above, and the Vezzani et al. publisher page. The search found relevant precedents for object-pose
estimation and pose-aware handover; it did not establish the novelty of the conditional information-limit
argument beyond this set.
