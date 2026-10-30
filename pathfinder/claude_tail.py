"""Evidence for a completed Claude turn followed by an interrupted background wake-up."""
import hashlib
import json
from pathlib import Path
from .provider_evidence import terminal_result_usage


def evidence(root, row, *, init_only=False):
    if (row.get('backend') != 'claude' or row.get('outcome') != 'completed'
            or row.get('exit_status') != (-9 if init_only else -15) or row.get('usage_completeness') != 'partial'
            or any(row.get(k) is not None for k in ('input_tokens', 'output_tokens'))):
        raise ValueError('not a completed Claude call with interrupted unknown tail')
    call = row['call_id']
    if not isinstance(call, str) or len(call) != 32 or any(c not in '0123456789abcdef' for c in call):
        raise ValueError('invalid tail call identity')
    path = Path(root) / 'transport-evidence' / f'{call}.events.jsonl'
    data = path.read_bytes()
    bound = (row.get('evidence_journal') or {}).get('events.jsonl') or {}
    sha = hashlib.sha256(data).hexdigest()
    if sha != bound.get('sha256') or len(data) != bound.get('size'):
        raise ValueError('Claude tail journal differs from receipt binding')
    lines = data.decode().splitlines()
    if not lines or lines[-1] != row.get('terminal_event'):
        raise ValueError('Claude tail terminal event differs')
    events = [json.loads(line) for line in lines]
    if any(not isinstance(e, dict) for e in events):
        raise ValueError('invalid Claude tail event')
    indices = [i for i,e in enumerate(events) if e.get('type') == 'result']
    if len(indices) != 1:
        raise ValueError('requires exactly one completed result')
    i = indices[0]; result = events[i]; tail = events[i+1:]
    usage = terminal_result_usage([lines[i]])
    if usage is None or result.get('is_error') is not False or result.get('subtype') != 'success':
        raise ValueError('missing complete successful first-result usage')
    if init_only:
        if (len(tail) != 1 or tail[0].get('type') != 'system' or tail[0].get('subtype') != 'init'
                or not result.get('session_id') or tail[0].get('session_id') != result['session_id']
                or tail[0].get('usage') is not None or row.get('usage') != usage):
            raise ValueError('requires exactly one same-session init and no later activity')
        return dict(journal_sha256=sha, journal_size=len(data), result_event_index=i,
                    completed_usage=usage,
                    completed_totals=dict(input_tokens=usage['input_tokens']+usage['cache_creation_input_tokens']+usage['cache_read_input_tokens'],output_tokens=usage['output_tokens']),
                    observed_tail_message_floor=dict(input_tokens=0,output_tokens=0),tail_samples=[],
                    tail_semantics='Init only: no observed assistant activity; in-flight provider usage is not certified zero.')
    if (not isinstance(result.get('session_id'),str) or not result['session_id']
            or not any(e.get('type') == 'system' and e.get('subtype') == 'task_notification' for e in tail)
            or not any(e.get('type') == 'system' and e.get('subtype') == 'init' for e in tail)
            or any(e.get('type') not in ('system','assistant') for e in tail)
            or any(e.get('type') == 'system' and e.get('subtype') not in ('task_updated','task_notification','background_tasks_changed','init','thinking_tokens') for e in tail)
            or any(e.get('session_id') != result.get('session_id') for e in tail)):
        raise ValueError('not an evidenced same-session background wake-up')
    samples = [(e.get('message') or {}).get('usage') for e in tail if e.get('type') == 'assistant']
    if not samples or samples[-1] != row.get('usage'):
        raise ValueError('missing matching partial assistant usage')
    keys = ('input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens')
    if any(not isinstance(s,dict) or any(type(s.get(k)) is not int or s[k]<0 for k in keys) for s in samples):
        raise ValueError('invalid partial usage')
    return dict(journal_sha256=sha,journal_size=len(data),result_event_index=i,
                completed_usage=usage,
                completed_totals=dict(input_tokens=usage['input_tokens']+usage['cache_creation_input_tokens']+usage['cache_read_input_tokens'],output_tokens=usage['output_tokens']),
                observed_tail_message_floor=dict(input_tokens=max(s['input_tokens']+s['cache_creation_input_tokens']+s['cache_read_input_tokens'] for s in samples),output_tokens=max(s['output_tokens'] for s in samples)),
                tail_samples=samples,tail_semantics='Partial message samples; not a measured tail total or upper bound.')
