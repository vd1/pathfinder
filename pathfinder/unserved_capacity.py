"""Recognise only a retained Codex capacity stream without observed model activity.

This is an evidence class for explicit uncertain reservations, not proof of zero billing.
"""
import hashlib
import json
import re
from pathlib import Path

MESSAGE = 'Selected model is at capacity. Please try a different model.'
WARNING = re.compile(r'Under-development features enabled: skip_host_skill_discovery\. '
    r'Under-development features are incomplete and may behave unpredictably\. '
    r'To suppress this warning, set `suppress_unstable_features_warning = true` in '
    r'/[^\n\r]+/config\.toml\.')


def evidence(root, row):
    if (row.get('backend') != 'codex' or row.get('outcome') != 'error'
            or row.get('error') != MESSAGE or (row.get('failure') or {}).get('class') != 'rate'
            or row.get('usage') is not None
            or any(row.get(k) is not None for k in ('input_tokens','output_tokens','cache_read','cache_write'))):
        raise ValueError('not a Codex capacity failure with unknown usage')
    call = row.get('call_id')
    if not isinstance(call,str) or not re.fullmatch('[0-9a-f]{32}',call):
        raise ValueError('invalid call identity')
    path = Path(root) / 'transport-evidence' / f'{call}.events.jsonl'
    data = path.read_bytes()
    binding = (row.get('evidence_journal') or {}).get('events.jsonl') or {}
    sha = hashlib.sha256(data).hexdigest()
    if sha != binding.get('sha256') or len(data) != binding.get('size'):
        raise ValueError('capacity journal differs from receipt binding')
    lines = data.decode().splitlines()
    if lines != row.get('raw_events') or not lines or lines[-1] != row.get('terminal_event'):
        raise ValueError('capacity events differ from receipt')
    events = [json.loads(line) for line in lines]
    if len(events)<4 or any(not isinstance(e,dict) for e in events):
        raise ValueError('invalid capacity event stream')
    first=events[0]
    if (set(first) != {'type','thread_id'} or first['type'] != 'thread.started'
            or not isinstance(first['thread_id'],str) or not first['thread_id']):
        raise ValueError('missing unique thread start')
    warnings=events[1:-3]
    for event in warnings:
        item=event.get('item')
        if (set(event) != {'type','item'} or event['type'] != 'item.completed'
                or not isinstance(item,dict) or set(item) != {'id','type','message'}
                or item['type'] != 'error' or not isinstance(item['id'],str)
                or not isinstance(item['message'],str) or not WARNING.fullmatch(item['message'])):
            raise ValueError('model activity or unrecognised CLI warning in capacity stream')
    if events[-3:] != [dict(type='turn.started'),dict(type='error',message=MESSAGE),
                        dict(type='turn.failed',error=dict(message=MESSAGE))]:
        raise ValueError('not the bounded no-observed-service capacity sequence')
    return dict(journal_sha256=sha,journal_size=len(data),event_count=len(events),
                cli_warning_count=len(warnings),observed_model_items=0,
                semantics='No model-produced item observed; actual provider usage remains unknown, not certified zero.')
