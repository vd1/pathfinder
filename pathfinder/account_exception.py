"""Exact owner-approved successor history exceptions and selected JSON custody."""
import json
from pathlib import Path
from . import pce, pce_evidence


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return pce._sha(canonical(value))


def _load(text):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate JSON key')
            out[key] = value
        return out
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def project(data, pointers):
    """Exact parsed values and a disjoint exhaustive omitted-subtree manifest."""
    if (not isinstance(pointers, list) or not pointers or len(pointers) > 1000
            or any(not isinstance(p, str) or not p.startswith('/') for p in pointers)
            or len(set(pointers)) != len(pointers)):
        raise pce.Changed('selected JSON needs unique absolute pointers')
    selected = {}
    for pointer in pointers:
        if any(other != pointer and pointer.startswith(other + '/') for other in pointers):
            raise pce.Changed('selected JSON pointers overlap')
        value = data
        for token in pointer[1:].split('/'):
            decoded = token.replace('~1', '/').replace('~0', '~')
            if decoded.replace('~', '~0').replace('/', '~1') != token:
                raise pce.Changed('noncanonical JSON pointer')
            if isinstance(value, list):
                if not decoded.isascii() or not decoded.isdigit() or str(int(decoded)) != decoded:
                    raise pce.Changed('invalid JSON array index')
                value = value[int(decoded)]
            elif isinstance(value, dict):
                value = value[decoded]
            else:
                raise pce.Changed('JSON pointer traverses a scalar')
        selected[pointer] = value
    omitted = []

    def entry(value, **where):
        omitted.append({**where, 'canonical_json_sha256': digest(value),
                        'canonical_json_bytes': len(canonical(value).encode('utf-8'))})

    def relevant(pointer):
        return pointer in selected or any(p.startswith(pointer + '/') for p in selected)

    def visit(value, pointer):
        if pointer in selected:
            return
        if not relevant(pointer):
            entry(value, pointer=pointer)
        elif isinstance(value, list):
            i = 0
            while i < len(value):
                if relevant(pointer + '/' + str(i)):
                    visit(value[i], pointer + '/' + str(i)); i += 1
                else:
                    end = i + 1
                    while end < len(value) and not relevant(pointer + '/' + str(end)):
                        end += 1
                    entry(value[i:end], array_pointer=pointer, start=i, end_exclusive=end)
                    i = end
        else:
            for key, child in value.items():
                visit(child, pointer + '/' + key.replace('~', '~0').replace('/', '~1'))
    visit(data, '')
    return selected, omitted


def selected_evidence(campaign, pair, spec):
    """Validate raw custody separately from the reviewer-visible exact projection."""
    if (not isinstance(spec, dict)
            or set(spec) != {'path', 'sha256', 'purpose', 'pointers', 'selected_sha256', 'omissions_sha256'}
            or not spec['path'].endswith('.json')):
        raise pce.Changed('invalid selected JSON custody specification')
    _, full = pce_evidence.validate(campaign, pair, {'version': 1, 'exclude': [], 'include': [
        {k: spec[k] for k in ('path', 'sha256', 'purpose')}]})
    text = full[spec['path']]
    try:
        selected, omitted = project(_load(text), spec['pointers'])
    except (ValueError, TypeError, KeyError, IndexError, RecursionError) as exc:
        raise pce.Changed('invalid selected JSON evidence') from exc
    if digest(selected) != spec['selected_sha256'] or digest(omitted) != spec['omissions_sha256']:
        raise pce.Changed('selected JSON values or omissions differ')
    document = canonical({
        'source': spec['path'], 'source_sha256': spec['sha256'],
        'scope': spec['purpose'],
        'visibility': 'Only the exact JSON subtrees below are supplied. Other source fields are not included.',
        'selected': selected})
    key = 'sources/external/selected-json-' + spec['sha256'][:16] + '.json'
    return {key: document}, {
        'specification': spec, 'source_bytes': len(text.encode('utf-8')),
        'selected_document_sha256': pce._sha(document), 'omitted_subtrees': omitted}


def authorize(packet, approval, pair, identity, delta, candidate):
    """No exception can be prepared without a distinct explicit approval artifact."""
    path = Path(packet) / 'history-exception.json'
    if not path.exists():
        if approval is not None:
            raise pce.Changed('approval supplied without a history exception')
        return None
    contract = json.loads(path.read_text())
    required = {'version', 'pair', 'identity', 'parent_pointer', 'parent_request_sha256',
                'parent_frozen_inputs_sha256', 'parent_candidate_sha256', 'parent_acceptance_sha256',
                'returned_findings_sha256', 'candidate_sha256', 'delta_sha256',
                'original_baseline_sha256', 'cumulative_sha256', 'existing_count', 'total_count',
                'finding_ids', 'selected_json'}
    if (set(contract) != required or contract['version'] != 1
            or contract['pair'] != pair or contract['identity'] != identity
            or contract['existing_count'] != 20 or contract['total_count'] != 23
            or contract['finding_ids'] != ['P1', 'P2', 'P3']
            or len(delta['changes']) != 3
            or [r['finding'] for r in delta['changes']] != contract['finding_ids']
            or contract['candidate_sha256'] != pce._sha(candidate)
            or contract['delta_sha256'] != digest(delta)
            or any(contract[k] != delta[k] for k in (
                'parent_candidate_sha256', 'parent_acceptance_sha256', 'returned_findings_sha256'))):
        raise pce.Changed('exact 23-record exception binding differs')
    if approval is None:
        raise pce.Changed('explicit owner approval of this exact history exception is required')
    receipt = json.loads(Path(approval).read_text())
    if (set(receipt) != {'version', 'decision', 'authority', 'approved_by', 'approval_reference', 'contract_sha256'}
            or receipt['version'] != 1 or receipt['decision'] != 'approve'
            or receipt['authority'] != 'owner'
            or any(not isinstance(receipt[k], str) or not receipt[k].strip()
                   for k in ('approved_by', 'approval_reference'))
            or receipt['contract_sha256'] != digest(contract)):
        raise pce.Changed('owner approval does not bind this exact history exception')
    return {'contract': contract, 'approval': receipt}


def replay(exception, original, cumulative, parent, selected, review):
    from . import account_register
    c = exception['contract']
    if (selected != c['parent_pointer'] or pce._sha(original) != c['original_baseline_sha256']
            or pce._sha((parent/'request.json').read_text()) != c['parent_request_sha256']
            or pce._sha((review/'frozen-inputs.json').read_text()) != c['parent_frozen_inputs_sha256']
            or len(cumulative['changes']) != 23 or digest(cumulative) != c['cumulative_sha256']):
        raise pce.Changed('approved 23-record parent or cumulative history differs')
    # Existing accepted-parent checks happen before this call. This validates every
    # sequential change without changing the ordinary revision length guard.
    candidate = original
    for change in cumulative['changes']:
        before, after = change['before'], change['after']
        if not before or candidate.count(before) != 1 or not after or before == after:
            raise pce.Changed('ambiguous exceptional replacement history')
        candidate = candidate.replace(before, after, 1)
    if pce._sha(candidate) != c['candidate_sha256']:
        raise pce.Changed('exceptional history has undeclared candidate edits')
    account_register.build(original, cumulative['changes'], candidate)
    return candidate


def custody(campaign, pair, root, request):
    record = request.get('selected_json_custody')
    if record is None:
        return
    documents, current = selected_evidence(campaign, pair, record['specification'])
    if current != record:
        raise pce.Changed('selected JSON custody changed')
    frozen = json.loads((root/'review/frozen-inputs.json').read_text())
    if any(frozen.get(name) != text for name, text in documents.items()):
        raise pce.Changed('selected JSON review visibility changed')
