"""Immutable, evidence-derived accounting corrections for retained failed Claude calls."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import re
from . import health, provider_evidence, provenance


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _path(c, call):
    if not isinstance(call, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', call):
        raise ValueError('invalid call identity')
    return c.path('usage-corrections') / f'{call}.json'


def _fields(c, row):
    if row.get('backend') != 'claude' or row.get('outcome') not in ('error', 'timeout'):
        raise ValueError('usage repair requires a failed Claude receipt')
    if row.get('input_tokens') is not None or row.get('output_tokens') is not None:
        raise ValueError('receipt already has accounting counters')
    evidence = (row.get('evidence_journal') or {}).get('events.jsonl') or {}
    path = c.path('transport-evidence') / f"{row['call_id']}.events.jsonl"
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != evidence.get('sha256') or len(data) != evidence.get('size'):
        raise ValueError('provider journal differs from receipt binding')
    lines = data.decode().splitlines()
    if not lines or lines[-1] != row.get('terminal_event'):
        raise ValueError('terminal result differs from receipt')
    usage = provider_evidence.terminal_result_usage(lines)
    if usage is None or usage != row.get('usage'):
        raise ValueError('no complete, matching terminal result usage')
    event = json.loads(lines[-1])
    if not event['is_error']:
        raise ValueError('recovery requires the saved failed terminal result')
    return dict(input_tokens=usage['input_tokens'], output_tokens=usage['output_tokens'],
                cache_read=usage['cache_read_input_tokens'], cache_write=usage['cache_creation_input_tokens'],
                usage_completeness='complete')


def effective(c, row):
    """Budget readers apply a validated overlay; the original receipt is never rewritten."""
    if not isinstance(row.get('call_id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', row['call_id']):
        return row
    path = _path(c, row['call_id'])
    if not path.exists():
        return row
    saved = json.loads(path.read_text())
    fields = _fields(c, row)
    if (saved.get('version') != 1 or saved.get('call_id') != row['call_id']
            or saved.get('receipt_sha256') != digest(row) or saved.get('original_receipt') != row
            or saved.get('fields') != fields
            or saved.get('sha256') != digest({k:v for k,v in saved.items() if k != 'sha256'})):
        raise ValueError('usage correction differs from bound provider evidence')
    return {**row, **fields, 'accounting_correction': str(path)}


@contextmanager
def _group_idle(c):
    if 'budget_group' not in c.raw:
        yield
        return
    from . import budget_group
    path, roots, _ = budget_group.load(c)
    with open(str(path)+'.lock', 'a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('budget group call is active; wait for idle admission') from None
        if any(any((root/'active-calls').glob('*.json')) for root in roots):
            raise ValueError('budget group has unresolved active-call evidence')
        yield


def recover(c, call, reason, *, apply=False, expected=None):
    target = _path(c, call)
    if not reason.strip():
        raise ValueError('an accounting correction needs a reason')
    with health.owner(c), _group_idle(c):
        if any(c.path('active-calls').glob('*.json')):
            raise ValueError('unresolved active-call evidence')
        if target.exists():
            raise ValueError('this call already has an accounting correction')
        data = c.path('receipts.jsonl').read_bytes()
        rows = [json.loads(line) for line in data.splitlines() if line.strip()]
        matching = [row for row in rows if row.get('call_id') == call]
        if not matching or any(row != matching[0] for row in matching):
            raise ValueError('missing or conflicting call receipts')
        row = matching[0]
        plan = dict(version=1,call_id=call,reason=reason.strip(),receipt_sha256=digest(row),
                    receipt_ledger_sha256=hashlib.sha256(data).hexdigest(),fields=_fields(c,row),
                    engine=provenance.engine(),original_receipt=row)
        plan['sha256'] = digest(plan)
        if not apply:
            return plan
        if expected != plan['sha256']:
            raise ValueError('accounting proposal changed; inspect before applying')
        target.parent.mkdir(exist_ok=True)
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(plan, stream, indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        return dict(correction=str(target),proposal_sha256=plan['sha256'],fields=plan['fields'],
                    next='inspect shared accounting, then canonical resume of the existing grant; no state or stop was changed')
