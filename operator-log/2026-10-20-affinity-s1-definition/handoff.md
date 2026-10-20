# Q053-P011 S1 definition

Existing engine `438592b029c9c39749a2bb95affa6a8ed1442806` supports this continuation without changes.
Use `/private/tmp/pathfinder-whole-body-438592b` and exact arguments in `action.json`, after verifying the
12 live bindings and idle ownership. This prepares one correction/check cycle, not a restart or PCE review.
No live grant, model call or deployment write was made by the maintainer.

The only change is a sentence immediately after the existing S1-partition sentence:

> S1 denotes a thrombin binding subpocket; its partition here is the associated residue group used in the
> authors' protein--ligand interaction-energy decomposition.

Three exact quotations in `context.json` establish the authors' binding-subpocket description, partition into
ligand-contacting groups, and S1 pocket group's role in the interaction-energy decomposition. Local `inputs/Q.txt`
is byte-identical to Q in the accepted external mapping. No residue boundary, primary-specificity convention,
substrate label, new numerical value, URL or source locator is added. No scientific script was executed.

The current canonical source is `correct-3`, not a refused manuscript. The immutable reason requires the
complete source to remain unchanged except for that sentence. `proposed-change.json` and the offline fixture
record the exact insertion; they do not authorise manual source installation. The calibration/RMSE clarifications,
C1 references, equations, limitations and original S1 sentence remain intact.

Four copied-account tests pass on the existing frozen runtime. The successful path uses corrector then fresh
checker, passes ordinary guard and host language checks, and passes a real canonical build. Removing the exact
added sentence reproduces `correct-3` byte-for-byte. Reference strings and the set of numerical tokens are unchanged.
All 85 acceptance-custody files and 755 prior files remain intact; only the expected presentation state,
publication status and continuation pointer change. Changed source, fabricated quote and altered prior-stage
history are rejected before calls. Stub clearance verifies the route, not the future live reviewer judgment.

See `audit.json` and `verification.json`. The operator's live result must be CLEARED before ordinary release.
The TeX test fixture retains inherited long-line layout; style bans pass. No engine upgrade or gate exception
is requested.
