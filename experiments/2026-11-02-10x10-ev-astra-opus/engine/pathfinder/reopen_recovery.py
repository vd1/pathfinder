"""Hash-bound recovery of a classic repair dispatched without its retained brief.

No new grant or scientific verdict: keep the existing grant and all charges,
archive the void attempt, restore only the last judged note, then permit the
ordinary runner to perform its bounded repair. No provider is called here.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
from pathlib import Path
from . import corpus, health, provenance, reopen, research, runner, transport


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _inventory(d):
    return {str(p.relative_to(d)): ('symlink:' + os.readlink(p) if p.is_symlink() else _sha(p))
            for p in sorted(d.rglob('*')) if (p.is_file() or p.is_symlink()) and p != d / 'lock'}


def _proposal(c, pair, snapshot, reason):
    if c.raw.get('research_scheme') or c.raw.get('research_bundles'):
        raise ValueError('recovery is only for the classic scheme')
    if not corpus.PAIR.fullmatch(pair) or not reason.strip():
        raise ValueError('pair identity and recovery reason required')
    d = c.thread_dir(pair); s = research.status(c, pair)
    grant = s.get('grant') or {}; records = reopen.records(c, pair)
    if (grant.get('grant') != 'repair' or not records or grant.get('n') != records[-1].get('n')
            or records[-1].get('from', {}).get('status') != 'PAUSE-ON-REVISE'
            or s.get('status') not in ('running', 'stopped')
            or s.get('stage') not in ('consolidate', 'verify') or s.get('repair')):
        raise ValueError('not an unbriefed active classic repair grant')
    if (d / 'verify-pending.json').exists() or s.get('pending'):
        raise ValueError('pending verifier/call evidence requires separate reconciliation')
    if (d / 'reopen-recoveries' / str(grant['n'])).exists():
        raise ValueError('this grant already has recovery evidence; no repeat recovery')
    review = reopen._last_verdict(d, pair)
    if (not review or review.get('decision') != 'REVISE' or not review.get('action')
            or review.get('round') != s.get('round')
            or review.get('at', '') > records[-1].get('at', '')
            or _sha(snapshot) != review.get('note_sha256')):
        raise ValueError('snapshot must match the last pre-grant REVISE note and corrections')
    if any(c.path('active-calls').glob('*.json')):
        raise ValueError('active-call evidence exists; wait for receipt and reconciliation')
    receipts = transport.receipts(c)
    after = [r for r in receipts if r.get('thread') == pair and r.get('at', '') >= records[-1]['at']
             and r.get('outcome') not in transport.UNCHARGED]
    if any(r.get('stage') != 'consolidate' or r.get('outcome') != 'completed'
           or any(type(r.get(k)) is not int or r[k] < 0 for k in ('input_tokens', 'output_tokens')) for r in after):
        raise ValueError('post-grant calls must be completed, accounted consolidations only')
    # Allocate a fresh retained-response slot without removing or overwriting the void response.
    repair = s.get('repairs', 0) + 1
    while (d / 'consolidation' / f"round-{s['round']}-repair-{repair}.json").exists():
        repair += 1
    files = _inventory(d)
    proposal = dict(version=1, pair=pair, grant=grant['n'], reason=reason.strip(),
                    snapshot=str(snapshot.resolve()), snapshot_sha256=_sha(snapshot),
                    files=files, receipts_sha256=_sha(c.path('receipts.jsonl')) if c.path('receipts.jsonl').exists() else None,
                    next_repair=repair, review=review,
                    retained_call_ids=[r.get('call_id') for r in after], engine=provenance.engine())
    proposal['sha256'] = hashlib.sha256(json.dumps(proposal, sort_keys=True).encode()).hexdigest()
    return proposal


def recover(c, pair, snapshot, reason, *, apply=False, expected=None):
    snapshot = Path(snapshot)
    with health.owner(c):
        owner = health.read(c.path('runner.json'))
        if owner and health.alive(owner.get('pid')):
            raise ValueError('recorded runner is alive; wait for it to drain')
        d = c.thread_dir(pair)
        with runner.Lock(d):
            plan = _proposal(c, pair, snapshot, reason)
            if not apply:
                return plan
            if expected != plan['sha256']:
                raise ValueError('recovery proposal hash differs; re-inspect before applying')
            custody = d / 'reopen-recoveries' / str(plan['grant'])
            custody.mkdir(parents=True, exist_ok=False)
            health.write(custody / 'proposal.json', plan)
            for name, digest in plan['files'].items():
                source = d / name; target = custody / 'before' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                if source.is_symlink():
                    target.symlink_to(os.readlink(source))
                else:
                    shutil.copyfile(source, target)
                actual = 'symlink:' + os.readlink(target) if target.is_symlink() else _sha(target)
                if actual != digest:
                    raise ValueError('source changed during archive; recovery stopped')
            note = snapshot.read_bytes()
            if hashlib.sha256(note).hexdigest() != plan['snapshot_sha256']:
                raise ValueError('snapshot changed during recovery')
            s = research.status(c, pair)
            research._atomic_write(d / f'{pair}.tex', note)
            research._set(c, pair, status='stopped', stage='consolidate', repair=plan['review'],
                          repairs=plan['next_repair'], failure=None,
                          reason='unbriefed repair archived; authorised grant awaits canonical resume')
            health.write(custody / 'applied.json', dict(proposal_sha256=plan['sha256'],
                         at=research._now(), grant_preserved=s['grant'],
                         note_sha256=plan['snapshot_sha256'], model_calls=0))
            return dict(proposal_sha256=plan['sha256'], custody=str(custody), status='stopped',
                        next='inspect custody, clear an operator stop if authorised, then canonical research resume')
