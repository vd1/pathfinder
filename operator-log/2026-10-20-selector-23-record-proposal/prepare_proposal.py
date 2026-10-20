"""Read retained records and write an approval-only proposal, never a live grant."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / '2026-10-20-selector-pool-component-contract'
THREAD = Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2/threads/Q010-P030')
PARENT = THREAD / 'edited/account-amendments/selector-definitions-20261020/revisions/model-decision-1'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def projection(source):
    """Exact JSON subtrees, with a disjoint exhaustive omitted-subtree inventory."""
    selected = {'/script_sha256': source['script_sha256']}
    for i, run in enumerate(source['runs']):
        for key in ('field', 'R', 'seed', 'counts'):
            selected[f'/runs/{i}/{key}'] = run[key]
        j = len(run['history']) - 1
        selected[f'/runs/{i}/history/{j}/accepted_shots'] = run['history'][j]['accepted_shots']
    omitted = []

    def visit(value, pointer):
        if pointer in selected:
            return
        if not any(p.startswith(pointer + '/') for p in selected):
            omitted.append({'pointer': pointer, 'canonical_json_sha256': digest(encoded(value)),
                            'canonical_json_bytes': len(encoded(value))})
            return
        if isinstance(value, list):
            start = 0
            while start < len(value):
                child_pointer = pointer + '/' + str(start)
                if any(s == child_pointer or s.startswith(child_pointer + '/') for s in selected):
                    visit(value[start], child_pointer)
                    start += 1
                    continue
                end = start + 1
                while end < len(value) and not any(
                        s == pointer + '/' + str(end) or s.startswith(pointer + '/' + str(end) + '/')
                        for s in selected):
                    end += 1
                omitted.append({'array_pointer': pointer, 'start': start, 'end_exclusive': end,
                    'canonical_json_sha256': digest(encoded(value[start:end])),
                    'canonical_json_bytes': len(encoded(value[start:end]))})
                start = end
            return
        items = value.items()
        for key, child in items:
            escaped = str(key).replace('~', '~0').replace('/', '~1')
            visit(child, pointer + '/' + escaped)
    visit(source, '')
    return selected, omitted


def main():
    bindings = json.loads((OLD / 'bindings.json').read_text())
    for name, expected in bindings.items():
        assert digest(Path(name).read_bytes()) == expected, name
    source = (PARENT / 'candidate.tex').read_text()
    changes = []

    def replace(finding, before, after):
        nonlocal source
        assert source.count(before) == 1
        changes.append({'finding': finding, 'before': before, 'after': after})
        source = source.replace(before, after, 1)

    replace('P1',
        r'Thus the three fields enter with equal weight; the denominator includes all accepted target-sector counts, not only those of the retained set.',
        r'Thus the three fields enter with equal weight; the denominator includes all accepted target-sector counts, not only those of the retained set. All sixty retained final field-run records have \(N_s>0\): the records cover \(R=16,32\), seeds \(0,\ldots,9\), and fields \(s=0,1/2,1\). The separately supplied selected-record evidence exposes each final target-sector count vector, its field, size and seed, and its final accepted-shot count from \texttt{ada/adapt\_qsci/result.json}. It does not embed the full result file, trajectories or earlier iteration histories; those omissions remain explicit.')
    replace('P2',
        r'Each field first retained at most \(R\) positive-count determinants, ordered by decreasing count and then increasing stored determinant index.',
        r'Each field first retained at most \(R\) positive-count determinants, ordered by decreasing count and then increasing stored determinant index. The retained implementation asserts that at least one target-sector count is positive before selecting determinants. A zero-accepted-count iteration therefore aborts at that assertion, before pooling; the implementation supplies no resampling, uniform-weight or dropped-field fallback. The pooling formula describes the retained positive-count runs, not a prescription for an unobserved zero-count field.')
    replace('P3',
        'Original endpoint calculations select their spaces independently: their endpoint-energy difference and vacuum static subtraction do not come from a common projector.',
        r'Original endpoint calculations select their spaces independently: their endpoint-energy difference and vacuum static subtraction do not come from a common projector. Specifically, let \(S_0\) and \(S_1\) be the independently selected vacuum and full-field spaces. The implementation takes \(E_0\) and its normalised ground-state vector from \(H_0|_{S_0}\), and \(E_1\) from the lowest eigenvalue of \(H_1|_{S_1}\). It extends the vacuum vector by zero to a vector \(u_0\) in the common 225-determinant parent basis. With \(V=H_1-H_0\) and the retained inactive-plus-nuclear endpoint increment \(\Delta c\), it evaluates \(D_{\mathrm{ind}}=u_0^{T}Vu_0+\Delta c\) and \(I_{\mathrm{ind}}=E_1-E_0+\Delta c-D_{\mathrm{ind}}\). Thus the static expectation uses the vacuum state in \(S_0\), whereas the full-field energy uses \(S_1\). The reported component errors subtract the exact-parent static and induction components and use the retained Hartree-to-kcal/mol conversion. This is the independently selected endpoint implementation, distinct from the common-space pooled calculation.')
    (HERE / 'account-candidate.tex').write_text(source)
    cumulative = json.loads((PARENT / 'request.json').read_text())['changes']
    assert len(cumulative['changes']) == 20
    write('successor-delta.json', {'parent_candidate_sha256': bindings[str(PARENT / 'candidate.tex')],
        'parent_acceptance_sha256': bindings[str(PARENT / 'acceptance.json')],
        'returned_findings_sha256': next(v for k, v in bindings.items() if k.endswith('amend-findings.json')),
        'changes': changes})
    write('cumulative-changes.json', {**cumulative, 'changes': cumulative['changes'] + changes})
    raw = (THREAD / 'ada/adapt_qsci/result.json').read_bytes()
    data = json.loads(raw)
    selected, omitted = projection(data)
    write('selected-result.json', {'policy': 'exact-json-pointer-subtrees-proposal-v1',
        'source': 'ada/adapt_qsci/result.json', 'source_sha256': digest(raw),
        'source_bytes': len(raw), 'selected': selected})
    write('visibility-manifest.json', {'status': 'proposed; unsupported by current canonical custody',
        'source_sha256': digest(raw), 'selected_pointers': list(selected), 'omitted_subtrees': omitted,
        'interpretation': 'Selected values are exact parsed JSON subtrees, not raw byte slices. Full source bytes are hash-bound and retained, not model-visible. Omitted entries are exhaustive disjoint subtrees, not assertions that their contents are irrelevant.',
        'old_external': {k: digest(v.encode()) for k, v in json.loads((PARENT / 'review/frozen-inputs.json').read_text()).items() if k.startswith('sources/external/')},
        'review_requirement': 'Every prior external input remains exact; add selected-result and this visibility manifest separately. All five roles see both new documents. Do not place projected text in raw evidence-snapshots.'})
    write('bindings.json', bindings)
    artifacts = ['account-candidate.tex', 'successor-delta.json', 'cumulative-changes.json',
                 'selected-result.json', 'visibility-manifest.json', 'bindings.json']
    write('proposal.json', {'status': 'AWAITING_OWNER_APPROVAL_AND_CANONICAL_IMPLEMENTATION',
        'apply_authorized': False, 'live_argv': None,
        'pair': 'Q010-P030', 'parent_pointer': {'id': 'selector-definitions-20261020', 'revision': 'model-decision-1'},
        'history_contract': {'existing_count': 20, 'exact_total': 23, 'new_count': 3,
            'ordinary_limit': 20, 'finding_ids': ['P1', 'P2', 'P3'],
            'rule': 'Permit only this exact bound cumulative history after explicit owner approval; retain all prior records in order and the original baseline. No generic maximum override or reset.'},
        'review_contract': {'passes': 1, 'fact_checks': 1, 'fresh_roles': ['author', 'archivist', 'fact-checker', 'critic', 'editor'],
            'providers': ['OpenAI'], 'pass_score': None, 'prompt_cap_unchanged': True,
            'rule': 'Normal strict gates and real build; selection changes only after genuine acceptance. No old scientific report used as new judgement.'},
        'approval_contract': 'A future canonical implementation must require an explicit owner-approved proposal digest and revalidate every live binding. This proposal carries no approval. No current engine accepts this extension.',
        'artifacts': {name: digest((HERE / name).read_bytes()) for name in artifacts}})


if __name__ == '__main__':
    main()
