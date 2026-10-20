# Q010-P030 ideal-control source context

This is a read-only diagnosis and quotation packet, not an executable grant. Presentation was running when
requested. No model call, scientific computation, deployment write, allowance or engine change was made.

## Supported definition

The retained ideal control uses fixed vacuum canonical RHF orbitals in its compact CAS. Its field parameter
scales the inherited MM charges: zero is vacuum, half is half field, and unity is full field. The field-only
space consists of the determinants with the largest exact parent ground-state probabilities at full field. The
pooled candidate set is the union of the top-R determinant lists at vacuum, half field and full field. It is
truncated to R by descending equal-weight sum of those three probabilities, with determinant index breaking
ties. This ideal deterministic construction is distinct from later finite-shot frequency pooling and from
screened component recombination.

Suggested bounded explanatory wording for review:

> Here field-only means selection from the exact parent ground-state probabilities at full MM-charge
> scaling. For the ideal pooled space, the candidates are the union of the top-R lists at vacuum, half field
> and full field; the R largest equal-weight summed probabilities are retained, with determinant index
> breaking ties.

Keep the existing numerical results, same-space endpoint evaluation, illustrative tolerance, fixed-orbital
restrictions and lack of universal pooling advantage unchanged. This packet does not address the separate CAS-
minus-RHF increment finding or establish which final correction route will be eligible.

## Evidence and validation

`context.json` contains four exact, unique, hash-bound quotations from retained `ada/water_selector.py` and
`ada/water_selector_interpretation.txt`. The interpretation note is byte-identical to its complete entry in
the accepted scientific supplement. The script is retained locally but is not embedded in that supplement;
this distinction is recorded explicitly in `evidence.json`. No script was executed.

The existing canonical `account_present._context` validator accepted the context using read-only paths.
Evidence bindings cover the original checker, first correction report, accepted supplement and acceptance
record. These are diagnostic bindings, not authorization to act on a changing presentation state.

## Route after presentation finishes

Do not interrupt or restart the current presentation. If the final state is an eligible cycle-limit or
guarded-correction PAUSE with the same unclear finding location, the existing `account-present-continue` route
can validate these quotations and bind the actual terminal state under an explicitly authorized single-cycle
grant. Recheck final finding location and source hashes first.

If canonical targeted review instead returns a confirmed scientific-definition finding and state RETURNED,
this context cannot bypass that result: existing `account_present.apply` accepts eligible PAUSE states only.
Use the supported accepted-successor amendment route bound to the actual returned finding and current
acceptance. No successor candidate, new allowance or cap exception is presumed by this packet.

No live action command is supplied while the final stage and findings remain unsettled.
