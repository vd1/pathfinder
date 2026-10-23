"""Explicit uncertain accounting, never a replacement for provider usage.

A proposal is inert. An approved proposal produces a new pinned group manifest;
operators still have to install that manifest under quiescent ownership.
"""
import hashlib
import json
from pathlib import Path

POLICY = 'served-capacity-reservation-v1'
NOTICE = 'Actual usage remains unknown; actual aggregate cap compliance is not certified.'
TOKENS = ('input_tokens', 'output_tokens')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def _keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError('reservation fields differ from contract')


def _receipt(root, call_id):
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


def _validate(proposal):
    _keys(proposal, ('version', 'policy', 'root', 'call_id', 'receipt', 'receipt_line_sha256',
                     'parent_manifest', 'parent_sha256', 'scope', 'reservation', 'rationale', 'notice'))
    if type(proposal['version']) is not int or proposal['version'] != 1 or proposal['policy'] != POLICY or proposal['notice'] != NOTICE:
        raise ValueError('unsupported reservation policy')
    root = Path(proposal['root'])
    if not root.is_absolute() or root != root.resolve():
        raise ValueError('reservation root must be canonical')
    parent = Path(proposal['parent_manifest'])
    data = parent.read_bytes()
    if hashlib.sha256(data).hexdigest() != proposal['parent_sha256']:
        raise ValueError('parent manifest changed')
    old = json.loads(data)
    if old.get('version') != 1 or set(old) != {'version', 'campaigns', 'budget'}:
        raise ValueError('reservation requires an unchanged version 1 group')
    if proposal['scope'] != {'campaigns': old['campaigns'], 'budget': old['budget']}:
        raise ValueError('reservation changed group scope or caps')
    if str(root) not in old['campaigns']:
        raise ValueError('reserved receipt is outside group')
    _keys(proposal['reservation'], TOKENS)
    for key in TOKENS:
        n = proposal['reservation'][key]
        if type(n) is not int or n <= 0 or n > old['budget'].get(key, -1):
            raise ValueError('reservation must be positive and within existing token caps')
    if not isinstance(proposal['rationale'], str) or not proposal['rationale'].strip():
        raise ValueError('reservation needs explicit estimate rationale')
    row, sha = _receipt(root, proposal['call_id'])
    if row != proposal['receipt'] or sha != proposal['receipt_line_sha256']:
        raise ValueError('original receipt or evidence changed')


def propose(campaign, call_id, input_tokens, output_tokens, rationale):
    from . import budget_group
    path, roots, cap = budget_group.load(campaign)
    row, sha = _receipt(campaign.root, call_id)
    proposal = dict(version=1, policy=POLICY, root=str(campaign.root.resolve()), call_id=call_id,
                    receipt=row, receipt_line_sha256=sha, parent_manifest=str(path),
                    parent_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    scope={'campaigns': [str(p) for p in roots], 'budget': cap},
                    reservation=dict(input_tokens=input_tokens, output_tokens=output_tokens),
                    rationale=rationale, notice=NOTICE)
    _validate(proposal)
    return proposal


def validate_record(record, scope):
    _keys(record, ('proposal', 'approval'))
    proposal, approval = record['proposal'], record['approval']
    _validate(proposal)
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
    return dict(version=2, **proposal['scope'], reservations=[record])


def records(doc):
    if doc['version'] == 1:
        return {}
    # Deliberately one explicitly approved exception, not an extensible waiver list.
    if not isinstance(doc.get('reservations'), list) or len(doc['reservations']) != 1:
        raise ValueError('version 2 requires exactly one approved reservation')
    p = validate_record(doc['reservations'][0], {k: doc[k] for k in ('campaigns', 'budget')})
    return {(p['root'], p['call_id']): p['reservation']}


def write_new(path, value):
    # Never overwrite a proposal, approval, manifest, receipt or previous result.
    with Path(path).open('x') as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
