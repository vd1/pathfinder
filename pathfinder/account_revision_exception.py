"""Exact owner-bound 24-to-26 pending-successor revisions; ordinary limits stay unchanged."""
import json
from pathlib import Path
from . import account_exception as ex, account_register, pce


def authorize(packet, approval, pair, identity, revision, delta, changes, candidate):
    path = Path(packet)/'revision-exception.json'
    if not path.exists():
        if approval is not None:
            raise pce.Changed('approval supplied without a revision history exception')
        return None, {}
    c = json.loads(path.read_text())
    required = {'version', 'pair', 'identity', 'revision', 'selected_pointer', 'selected_acceptance_sha256',
                'parent_pointer', 'parent_history_sha256', 'parent_candidate_sha256',
                'parent_result_sha256', 'parent_frozen_inputs_sha256', 'original_baseline_sha256',
                'candidate_sha256', 'delta_sha256', 'cumulative_sha256', 'existing_count', 'total_count',
                'finding_ids', 'evidence_projection_sha256'}
    projection = delta.get('evidence_projection')
    if (set(c) != required or c['version'] != 1 or c['pair'] != pair or c['identity'] != identity
            or c['revision'] != revision or c['existing_count'] != 24 or c['total_count'] != 26
            or len(delta['changes']) != 2 or len(changes['changes']) != 26
            or len(c['finding_ids']) != 2
            or c['finding_ids'] != [r['finding'] for r in delta['changes']]
            or c['candidate_sha256'] != pce._sha(candidate) or c['delta_sha256'] != ex.digest(delta)
            or c['cumulative_sha256'] != ex.digest(changes)
            or c['parent_candidate_sha256'] != delta['parent_candidate_sha256']
            or c['evidence_projection_sha256'] != ex.digest(projection)
            or not isinstance(projection, dict) or set(projection) != {'version','exclude','include'}
            or projection['version'] != 1 or projection['exclude']
            or not isinstance(projection['include'], list) or len(projection['include']) != 1
            or any('json_fields' in row for row in projection['include'])):
        raise pce.Changed('exact 26-record revision contract differs')
    scope = delta.get('operator_evidence_visibility')
    if (not isinstance(scope, dict) or set(scope) != {'kind','authority','parent_candidate_sha256','source','change','append'}
            or scope['kind'] != 'operator-evidence-visibility-v1'
            or not isinstance(scope['authority'], str) or not scope['authority'].strip()
            or scope['parent_candidate_sha256'] != delta['parent_candidate_sha256']
            or scope['source'] != projection['include'][0]['path']
            or scope['change'] != delta['changes'][1]
            or scope['change']['finding'] != 'operator-evidence-visibility'
            or not isinstance(scope['append'], str) or not scope['append'].strip()
            or scope['change']['after'] != scope['change']['before'] + scope['append']):
        raise pce.Changed('exact operator evidence-visibility append differs')
    if approval is None:
        raise pce.Changed('explicit owner approval of this exact 26-record revision is required')
    receipt = json.loads(Path(approval).read_text())
    if (set(receipt) != {'version','decision','authority','approved_by','approval_reference','contract_sha256'}
            or receipt['version'] != 1 or receipt['decision'] != 'approve' or receipt['authority'] != 'owner'
            or any(not isinstance(receipt[k], str) or not receipt[k].strip()
                   for k in ('approved_by','approval_reference'))
            or receipt['contract_sha256'] != ex.digest(c)):
        raise pce.Changed('owner approval does not bind this exact revision exception')
    return {'contract': c, 'approval': receipt}, projection


def replay(campaign, pair, exception, *, successor_mode, selected, pending, parent, review,
           history, old_request, original, changes, candidate):
    from . import account_amend
    c = exception['contract']
    accepted = account_amend._root(campaign, pair, selected['id'])/'acceptance.json'
    if (not successor_mode or selected != c['selected_pointer'] or pending != c['parent_pointer']
            or pce._sha(accepted.read_text()) != c['selected_acceptance_sha256']
            or ex.digest(history) != c['parent_history_sha256']
            or pce._sha((review/'result.json').read_text()) != c['parent_result_sha256']
            or pce._sha((review/'frozen-inputs.json').read_text()) != c['parent_frozen_inputs_sha256']
            or pce._sha(original) != c['original_baseline_sha256']
            or len(old_request['changes']['changes']) != 24
            or changes['changes'][:24] != old_request['changes']['changes']):
        raise pce.Changed('pending successor history or selected acceptance differs')
    text = original
    for row in changes['changes']:
        before, after = row['before'], row['after']
        if not before or text.count(before) != 1 or not after or before == after:
            raise pce.Changed('ambiguous exceptional revision history')
        text = text.replace(before, after, 1)
    if text != candidate:
        raise pce.Changed('exceptional revision has undeclared edits')
    account_register.build(original, changes['changes'], candidate)
    return text
