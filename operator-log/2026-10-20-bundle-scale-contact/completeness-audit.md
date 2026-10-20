# Spring-scale and contact-definition audit

This audit addresses exactly the accepted publication's confirmed P1 and P2. It distinguishes the restoration
benchmark from the separate deposited-network mode calculation. No retained scientific code is executed.

| Definition | Exact retained basis | Clarification |
| --- | --- | --- |
| Unit spring matrix | Branch-3 `check_ligand_enm.py`, `edge` and baseline assembly | Every cutoff-selected baseline edge contributes the outer product of a two-node Cartesian distance gradient. Direction is divided by edge length; the whole vector is not implicitly treated as a one-node unit vector. |
| Scales 1 and 2 | Same script, `spring`, `a/s`, `b/s`; joint `full_deletion_check.py` | Relative numerical scaling of the unit matrix. Earlier stiffening and corrected restoration are distinguished. Common proportional scaling of all four restoration corners cancels in the dimensionless cycle. No physical force constant or energy-per-length-squared unit is invented. |
| Coordinates and cutoff | Direct parsing and assembly in retained scripts | Coordinates and cutoffs are angstrom-valued. This does not assign physical force-constant calibration to the numerical spring multiplier. All previous cutoff, bundle, rank and sensitivity qualifications remain. |
| Exact mode contact | `mode-results.json`, ligand-inclusive, 8 angstrom, no remedy | H216 GLY CA and H1501 22U C13. The code selects nearest ligand heavy node to Gly216 CA. It is not the N1 intervention bundle, a carbonyl contact or the conditioning module's earlier closest-any-ligand observable. |
| Gradient and restriction | `check_modes.py`, `audit`; imported `check_networks.py` | Positive unit direction at Gly216 CA, negative at C13, zeros elsewhere. Six Euclidean rigid modes removed analytically; Cartesian-normalised internal eigenvectors. No mass weighting or extra whole-gradient normalisation is inferred. |
| Self-response and share | Explicit overlap/spectral sum and saved mode row | Sum of squared mode overlaps divided by positive eigenvalues; lowest-mode contribution divided by the complete sum. The reported share is dimensionless, not absolute variance or calibrated force-field response. |
| Protein-only alternative | Same selection code and stored identities | Nearest CA beyond 4 angstroms, recorded Gly226 CA, is separately identified and explicitly not the quoted ligand-inclusive contact. |
| Model and cost limits | Existing accepted text and retained scripts | Proxy-only status, separate restoration/mode networks, no Q molecular validation and no cheaper-readout inference are unchanged. Existing remedy, alignment and fraction results remain. |
| Evidence transport | Complete inherited nine-file supplement plus five exact files | No original payload is omitted. Full scientific scripts and result JSON are added with hashes. The mode note contains prior-review commentary and is not newly transported; its needed scientific definitions are present in the complete scripts/results. |

The script inspection and saved-row lookup identify definitions, not new scientific computation. Exact reverse
replacement reconstructs the genuine accepted parent; all prior numeric tokens are retained. The two bounded
changes bind P1/P2 and preserve the old acceptance until genuine fresh review and canonical build succeed.
