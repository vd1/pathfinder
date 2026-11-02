"""Explicit uncertain accounting, never a replacement for provider usage.

A proposal is inert. An approved proposal produces a new pinned group manifest;
operators still have to install that manifest under quiescent ownership.
"""
import hashlib
import json
from pathlib import Path

POLICY = 'served-capacity-reservation-v1'
UNSERVED_POLICY = 'unserved-capacity-reservation-v1'
CLAUDE_TAIL_POLICY = 'claude-post-result-reservation-v1'
CLAUDE_INIT_POLICY = 'claude-init-tail-reservation-v1'
SERVED_EXTENSION = 'served-capacity-extension-v1'
UNSERVED_EXTENSION = 'unserved-capacity-extension-v1'
CAPACITY_EXTENSIONS = (SERVED_EXTENSION, UNSERVED_EXTENSION)
UNSERVED_POLICIES = (UNSERVED_POLICY, UNSERVED_EXTENSION)
ORPHAN_POLICY = 'reboot-orphan-reservation-v1'
TAIL_POLICIES = (CLAUDE_TAIL_POLICY, CLAUDE_INIT_POLICY)
NOTICE = 'Actual usage remains unknown; actual aggregate cap compliance is not certified.'
TOKENS = ('input_tokens', 'output_tokens')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def _keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError('reservation fields differ from contract')


def _receipt(root, call_id, policy=POLICY):
    if policy == ORPHAN_POLICY:
        from . import config, orphan_recovery
        return orphan_recovery.evidence_receipt(config.campaign_from(Path(root), json.loads((Path(root)/'campaign.json').read_text())), call_id)
    matches = []
    for line in (Path(root) / 'receipts.jsonl').read_bytes().splitlines(keepends=True):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get('call_id') == call_id:
            matches.append((row, hashlib.sha256(line).hexdigest()))
    if len(matches) != 1:
        raise ValueError('reservation requires exactly one original receipt')
    row, sha = matches[0]
    if policy == SERVED_EXTENSION:
        from .served_capacity import evidence
        evidence(root,row)
        return row,sha
    if policy in TAIL_POLICIES:
        from .claude_tail import evidence
        evidence(root, row, init_only=policy == CLAUDE_INIT_POLICY)
        return row, sha
    if policy in UNSERVED_POLICIES:
        from .unserved_capacity import evidence
        evidence(root,row)
        return row,sha
    events = [json.loads(event) for event in row.get('raw_events') or []]
    message = 'Selected model is at capacity. Please try a different model.'
    if not (row.get('backend') == 'codex' and row.get('outcome') == 'error'
            and row.get('error') == message and (row.get('failure') or {}).get('class') == 'rate'
            and row.get('usage') is None and all(row.get(k) is None for k in TOKENS)
            and any(e.get('type') == 'thread.started' for e in events)
            and any(e.get('type') == 'item.completed' and
                    (e.get('item') or {}).get('type') in ('agent_message', 'command_execution') for e in events)
            and events and events[-1].get('type') == 'turn.failed'
            and (events[-1].get('error') or {}).get('message') == message):
        raise ValueError('receipt is not an evidenced partially served capacity failure with unknown usage')
    return row, sha


def _validate(proposal, *, parent_validated=False):
    policy = proposal.get('policy')
    _keys(proposal, ('version', 'policy', 'root', 'call_id', 'receipt', 'receipt_line_sha256',
                     'parent_manifest', 'parent_sha256', 'scope', 'reservation', 'rationale', 'notice') + (('claude_tail',) if policy in TAIL_POLICIES else ()) + (('unserved_evidence',) if policy in UNSERVED_POLICIES else ()) + (('served_evidence',) if policy == SERVED_EXTENSION else ()))
    if type(proposal['version']) is not int or proposal['version'] != 1 or policy not in (POLICY, UNSERVED_POLICY, ORPHAN_POLICY, *CAPACITY_EXTENSIONS, *TAIL_POLICIES) or proposal['notice'] != NOTICE:
        raise ValueError('unsupported reservation policy')
    root = Path(proposal['root'])
    if not root.is_absolute() or root != root.resolve():
        raise ValueError('reservation root must be canonical')
    parent = Path(proposal['parent_manifest'])
    data = parent.read_bytes()
    if hashlib.sha256(data).hexdigest() != proposal['parent_sha256']:
        raise ValueError('parent manifest changed')
    old = json.loads(data)
    if policy in CAPACITY_EXTENSIONS:
        if type(old.get('version')) is not int or old.get('version') not in (2,3,4,5,6) or set(old)!={'version','campaigns','budget','reservations'}:
            raise ValueError('capacity extension requires an approved reservation group')
        if not parent_validated and (str(root),proposal['call_id']) in records(old):
            raise ValueError('call already reserved')
    elif policy in (CLAUDE_INIT_POLICY, ORPHAN_POLICY):
        if old.get('version') != 2 or set(old) != {'version','campaigns','budget','reservations'}:
            raise ValueError('extension requires an unchanged version 2 group')
        previous = records(old)
        if (str(root),proposal['call_id']) in previous:
            raise ValueError('call already reserved')
    elif old.get('version') != 1 or set(old) != {'version', 'campaigns', 'budget'}:
        raise ValueError('reservation requires an unchanged version 1 group')
    if proposal['scope'] != {'campaigns': old['campaigns'], 'budget': old['budget']}:
        raise ValueError('reservation changed group scope or caps')
    if str(root) not in old['campaigns']:
        raise ValueError('reserved receipt is outside group')
    _keys(proposal['reservation'], TOKENS)
    for key in TOKENS:
        n = proposal['reservation'][key]
        if type(n) is not int or n < (0 if policy in UNSERVED_POLICIES else 1) or n > old['budget'].get(key, -1):
            raise ValueError('reservation must satisfy its policy minimum and existing token caps')
    if not isinstance(proposal['rationale'], str) or not proposal['rationale'].strip():
        raise ValueError('reservation needs explicit estimate rationale')
    row, sha = _receipt(root, proposal['call_id'], policy)
    if row != proposal['receipt'] or sha != proposal['receipt_line_sha256']:
        raise ValueError('original receipt or evidence changed')
    if policy == SERVED_EXTENSION:
        from .served_capacity import evidence
        if proposal['served_evidence'] != evidence(root,row):raise ValueError('served evidence changed')
    if policy in UNSERVED_POLICIES:
        from .unserved_capacity import evidence
        if proposal['unserved_evidence'] != evidence(root,row):
            raise ValueError('unserved evidence classification changed')
    if policy in TAIL_POLICIES:
        from .claude_tail import evidence
        basis = evidence(root, row, init_only=policy == CLAUDE_INIT_POLICY)
        if basis != proposal['claude_tail']:
            raise ValueError('Claude completed/tail evidence changed')
        if any(proposal['reservation'][k] < basis['completed_totals'][k] + max(1,basis['observed_tail_message_floor'][k]) for k in TOKENS):
            raise ValueError('reservation must include completed totals plus an estimate covering observed tail samples')


def propose(campaign, call_id, input_tokens, output_tokens, rationale, policy=POLICY):
    from . import budget_group
    path, roots, cap = budget_group.load(campaign)
    row, sha = _receipt(campaign.root, call_id, policy)
    proposal = dict(version=1, policy=policy, root=str(campaign.root.resolve()), call_id=call_id,
                    receipt=row, receipt_line_sha256=sha, parent_manifest=str(path),
                    parent_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    scope={'campaigns': [str(p) for p in roots], 'budget': cap},
                    reservation=dict(input_tokens=input_tokens, output_tokens=output_tokens),
                    rationale=rationale, notice=NOTICE)
    if policy in TAIL_POLICIES:
        from .claude_tail import evidence
        proposal['claude_tail'] = evidence(campaign.root, row, init_only=policy == CLAUDE_INIT_POLICY)
    if policy in UNSERVED_POLICIES:
        from .unserved_capacity import evidence
        proposal['unserved_evidence'] = evidence(campaign.root,row)
    if policy == SERVED_EXTENSION:
        from .served_capacity import evidence
        proposal['served_evidence']=evidence(campaign.root,row)
    _validate(proposal)
    return proposal


def validate_record(record, scope, *, parent_validated=False):
    _keys(record, ('proposal', 'approval'))
    proposal, approval = record['proposal'], record['approval']
    _validate(proposal,parent_validated=parent_validated)
    _keys(approval, ('proposal_sha256', 'approved', 'accept_unknown_usage',
                     'accept_uncertified_actual_total', 'approved_by', 'approved_at', 'authority'))
    if (approval['proposal_sha256'] != digest(proposal)
            or any(approval[k] is not True for k in ('approved', 'accept_unknown_usage',
                                                     'accept_uncertified_actual_total'))
            or any(not isinstance(approval[k], str) or not approval[k].strip()
                   for k in ('approved_by', 'approved_at', 'authority'))):
        raise ValueError('explicit approval does not match reservation proposal and uncertainty')
    if proposal['scope'] != scope:
        raise ValueError('reservation scope or caps differ')
    return proposal


def approved_manifest(proposal, approval):
    record = dict(proposal=proposal, approval=approval)
    validate_record(record, proposal['scope'])
    if proposal['policy'] in CAPACITY_EXTENSIONS:
        parent=json.loads(Path(proposal['parent_manifest']).read_text())
        return dict(version=6 if proposal['policy']==UNSERVED_EXTENSION else 5, **proposal['scope'], reservations=[*parent['reservations'],record])
    if proposal['policy'] in (CLAUDE_INIT_POLICY, ORPHAN_POLICY):
        parent = json.loads(Path(proposal['parent_manifest']).read_text())
        return dict(version=4 if proposal['policy'] == ORPHAN_POLICY else 3, **proposal['scope'], reservations=[*parent['reservations'],record])
    return dict(version=2, **proposal['scope'], reservations=[record])


def records(doc):
    if doc.get('version') in (5,6):
        # Walk the append-only chain once; no exponential revalidation on recurrence.
        chain=[];seen=set();current=doc
        while current.get('version') in (5,6):
            _keys(current,('version','campaigns','budget','reservations'))
            saved=current['reservations']
            if not isinstance(saved,list) or not saved:raise ValueError('empty served extension')
            record=saved[-1];p=record['proposal']
            if p.get('policy')!=(SERVED_EXTENSION if current['version']==5 else UNSERVED_EXTENSION):raise ValueError('capacity extension policy differs from group version')
            identity=(p['root'],p['call_id'])
            if identity in seen:raise ValueError('call already reserved')
            seen.add(identity)
            parent=json.loads(Path(p['parent_manifest']).read_text())
            if saved[:-1]!=parent.get('reservations'):raise ValueError('prior reservations changed')
            chain.append((current,record));current=parent
        previous=records(current)
        for current,record in reversed(chain):
            p=validate_record(record,{k:current[k] for k in ('campaigns','budget')},parent_validated=True)
            identity=(p['root'],p['call_id'])
            if identity in previous:raise ValueError('call already reserved')
            previous[identity]=p['reservation']
        return previous
    if doc['version'] == 1:
        return {}
    scope = {k: doc[k] for k in ('campaigns','budget')}
    saved = doc.get('reservations')
    if doc['version'] == 2:
        if not isinstance(saved,list) or len(saved) != 1 or saved[0]['proposal'].get('policy') in (CLAUDE_INIT_POLICY, ORPHAN_POLICY, *CAPACITY_EXTENSIONS):
            raise ValueError('version 2 requires exactly one approved reservation')
        p = validate_record(saved[0],scope)
        return {(p['root'],p['call_id']):p['reservation']}
    if doc['version'] not in (3, 4) or not isinstance(saved,list) or len(saved) != 2:
        raise ValueError('extension requires an inherited reservation plus one approved exception')
    if saved[1]['proposal'].get('policy') != (ORPHAN_POLICY if doc['version'] == 4 else CLAUDE_INIT_POLICY):
        raise ValueError('reservation policy differs from group version')
    p = validate_record(saved[1],scope)
    parent = json.loads(Path(p['parent_manifest']).read_text())
    if saved[:-1] != parent['reservations']:
        raise ValueError('prior reservation or approval changed')
    previous = records(parent)
    return {**previous,(p['root'],p['call_id']):p['reservation']}


def write_new(path, value):
    # Never overwrite a proposal, approval, manifest, receipt or previous result.
    with Path(path).open('x') as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
