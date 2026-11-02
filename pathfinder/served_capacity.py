"""Retained Codex capacity failure after observed service, with no reported usage."""
import hashlib,json,re
from pathlib import Path
from .unserved_capacity import MESSAGE

def evidence(root,row):
    if (row.get('backend')!='codex' or row.get('outcome')!='error'
            or row.get('error')!=MESSAGE or (row.get('failure') or {}).get('class')!='rate'
            or row.get('usage') is not None
            or any(row.get(k) is not None for k in ('input_tokens','output_tokens','cache_read','cache_write'))):
        raise ValueError('requires a served Codex capacity failure with unknown usage')
    call=row.get('call_id')
    if not isinstance(call,str) or not re.fullmatch('[0-9a-f]{32}',call):raise ValueError('invalid call identity')
    data=(Path(root)/'transport-evidence'/f'{call}.events.jsonl').read_bytes()
    sha=hashlib.sha256(data).hexdigest();binding=(row.get('evidence_journal') or {}).get('events.jsonl') or {}
    if sha!=binding.get('sha256') or len(data)!=binding.get('size'):raise ValueError('capacity journal binding differs')
    lines=data.decode().splitlines()
    from . import gc
    if (row.get('raw_events') not in (lines,gc.compact_events(lines))) or not lines or lines[-1]!=row.get('terminal_event'):raise ValueError('capacity receipt events differ')
    events=[json.loads(x) for x in lines]
    if any(not isinstance(e,dict) for e in events):raise ValueError('invalid capacity events')
    if (events[0].get('type')!='thread.started'
            or sum(e.get('type')=='thread.started' for e in events)!=1
            or sum(e.get('type')=='turn.started' for e in events)!=1
            or sum(e.get('type')=='turn.failed' for e in events)!=1
            or any(e.get('type') in ('turn.completed','result') or e.get('usage') is not None for e in events)
            or events[-1]!=dict(type='turn.failed',error=dict(message=MESSAGE))):
        raise ValueError('not a single failed capacity turn without reported usage')
    produced=[e['item'] for e in events if e.get('type')=='item.completed' and isinstance(e.get('item'),dict)
              and e['item'].get('type') in ('command_execution','agent_message','reasoning')]
    if not produced:raise ValueError('no observed served model item')
    return dict(journal_sha256=sha,journal_size=len(data),event_count=len(events),
                completed_model_items=len(produced),
                semantics='Observed model service; actual usage unknown. Each call requires a separately approved reservation.')
