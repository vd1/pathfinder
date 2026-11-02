"""Host reconstruction of a reboot-interrupted Codex peer, never a provider response."""
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone
from . import health


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def boot_time():
    if Path('/proc/stat').exists():
        for line in Path('/proc/stat').read_text().splitlines():
            if line.startswith('btime '):return int(line.split()[1])
    text=subprocess.check_output(['sysctl','-n','kern.boottime'],text=True)
    match=re.search(r'\bsec = (\d+)',text)
    if not match:raise ValueError('cannot establish current host boot time')
    return int(match[1])


def _paths(c,call):
    if not isinstance(call,str) or not re.fullmatch('[0-9a-f]{32}',call):raise ValueError('invalid orphan identity')
    return c.path(f'active-calls/{call}.json'),c.path(f'orphan-recoveries/{call}.json')


def _journal(c,call):
    path=c.path(f'transport-evidence/{call}.events.jsonl');data=path.read_bytes()
    events=[json.loads(x) for x in data.decode().splitlines()]
    if (not events or any(not isinstance(e,dict) for e in events)
            or events[0].get('type')!='thread.started'
            or any(e.get('type') in ('turn.completed','turn.failed','result') for e in events)
            or not any(e.get('type')=='item.completed' and (e.get('item') or {}).get('type')=='command_execution' for e in events)):
        raise ValueError('not an incomplete served Codex journal')
    return dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data))


def _rows(c):
    p=c.path('receipts.jsonl')
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def _receipt(snapshot):
    a=snapshot['active_call'];call=a['attempt_id']
    return dict(v=3,call_id=call,at=datetime.fromtimestamp(snapshot['boot_time'],timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                run_id=a['run_id'],thread=a['thread'],stage=a['stage'],actor=a['actor'],backend='codex',model=None,
                outcome='interrupted',error='Host reboot interrupted the peer; no provider final result or usage.',
                usage=None,input_tokens=None,output_tokens=None,cache_read=None,cache_write=None,cost=None,
                usage_completeness='unknown',seconds=snapshot['elapsed_upper_bound_seconds'],
                host_recovery=dict(origin='host-orphan-recovery-v1',snapshot_sha256=digest(snapshot),
                                   peer_phase=snapshot['peer_phase'],prior_peer_ids=snapshot['prior_peer_ids'],
                                   seconds_semantics='Conservative elapsed upper bound to next host boot, not provider duration.'),
                evidence_journal={'events.jsonl':snapshot['journal']})


def inspect(c,call):
    active,archive=_paths(c,call)
    if archive.exists():
        saved=json.loads(archive.read_text());s=saved.get('snapshot')
        if not isinstance(s,dict) or saved.get('sha256')!=digest(s) or s.get('root')!=str(c.root.resolve()) or s['active_call']['attempt_id']!=call:
            raise ValueError('orphan snapshot changed')
        if active.exists() and json.loads(active.read_text())!=s['active_call']:raise ValueError('active record changed')
        if _journal(c,call)!=s['journal']:raise ValueError('orphan journal changed')
        return saved
    if any(r.get('call_id')==call for r in _rows(c)):raise ValueError('orphan already has a receipt without recovery snapshot')
    a=json.loads(active.read_text());boot=boot_time()
    if (a.get('attempt_id')!=call or a.get('stage')!='peer' or a.get('actor') not in c.peers
            or health.alive(a.get('pid')) is not False or health.alive(a.get('child_pid')) is not False
            or type(a.get('started_at')) not in (int,float) or not a['started_at']<boot
            or type(a.get('timeout_seconds')) not in (int,float) or a['timeout_seconds']<=0):
        raise ValueError('requires a proven dead, pre-boot peer attempt')
    d=c.thread_dir(a['thread']);state=json.loads((d/'status.json').read_text())
    if state.get('stage')!='peers' or state.get('status') not in ('running','stopped') or c.raw.get('research_scheme'):
        raise ValueError('requires an unfinished classic peer phase')
    ledger=[json.loads(x) for x in (d/'ledger.jsonl').read_text().splitlines() if x.strip()]
    review=max((x['seq'] for x in ledger if x['actor']=='verifier' and x['kind']=='review' and x['text'].startswith('ITERATE:')),default=0)
    phase=dict(round=state['round'],review_seq=max(review,(state.get('grant') or {}).get('ready_after') or 0))
    rows=[r for r in _rows(c) if r.get('thread')==a['thread']]
    cut=max((i for i,r in enumerate(rows) if r.get('stage')=='verify' and r.get('outcome')=='completed'),default=-1)
    prior=[r['call_id'] for r in rows[cut+1:] if r.get('stage')=='peer' and r.get('outcome') not in ('refused','launch failed','no session')]
    # Immutable host snapshots preserve stale runner metadata while ordinary resume replaces live metadata.
    files=[c.path('runner.json'),d/'status.json',d/'ledger.jsonl',c.path('campaign.json')]
    parent=c.raw.get('parent')
    if parent:files += [(c.root/parent).resolve()/name for name in ('runner.json','progress.json')]
    historical={str(p):p.read_text() for p in files if p.exists()}
    s=dict(version=1,root=str(c.root.resolve()),active_call=a,boot_time=boot,journal=_journal(c,call),
           elapsed_upper_bound_seconds=math.ceil(boot-a['started_at']),
           peer_phase=phase,prior_peer_ids=prior,historical_files=historical)
    return dict(snapshot=s,sha256=digest(s))


def evidence_receipt(c,call):
    saved=inspect(c,call);row=_receipt(saved['snapshot'])
    matches=[r for r in _rows(c) if r.get('call_id')==call]
    if matches and (len(matches)!=1 or matches[0]!=row):raise ValueError('host recovery receipt differs')
    line=json.dumps(row,sort_keys=True)+'\n'
    if matches:
        actual=[x for x in c.path('receipts.jsonl').read_bytes().splitlines(keepends=True) if x.strip() and json.loads(x).get('call_id')==call]
        if actual!=[line.encode()]:raise ValueError('host recovery receipt bytes changed')
    return row,hashlib.sha256(line.encode()).hexdigest()


def recover(c,call,*,apply=False,expected=None):
    from . import budget_group
    active,archive=_paths(c,call)
    with health.owner(c):
        group,roots,_=budget_group.load(c)
        with Path(str(group)+'.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if any(p!=active for root in roots for p in (root/'active-calls').glob('*.json')):
                raise ValueError('other active-call evidence must be resolved first')
            saved=inspect(c,call)
            if not apply:return {**saved,'prospective_host_receipt':_receipt(saved['snapshot'])}
            if expected!=saved['sha256']:raise ValueError('orphan evidence changed; inspect again')
            if not archive.exists():
                archive.parent.mkdir(exist_ok=True)
                with archive.open('x') as f:json.dump(saved,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
            row,_=evidence_receipt(c,call)
            if not any(r.get('call_id')==call for r in _rows(c)):
                with c.path('receipts.jsonl').open('a') as f:
                    f.write(json.dumps(row,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
            if active.exists():
                if json.loads(active.read_text())!=saved['snapshot']['active_call']:raise ValueError('active record changed')
                health.retire_orphans(c,{row['thread']})
            return dict(snapshot=str(archive),sha256=saved['sha256'],host_receipt=call,
                        usage='unknown; requires separately approved reservation',model_calls=0)


def peer_carry(c,pair,phase):
    """Only repaired phases carry spent turns across restarts; normal phases are unchanged."""
    from . import transport
    rows=transport.receipts(c)
    recovered=[(i,r) for i,r in enumerate(rows) if r.get('thread')==pair and (r.get('host_recovery') or {}).get('peer_phase')==phase]
    if not recovered:return {},{}
    first=recovered[0][0];ids=set()
    for _,r in recovered:
        evidence_receipt(c,r['call_id'])
        ids.update(r['host_recovery']['prior_peer_ids'])
    chosen=[r for i,r in enumerate(rows) if r.get('thread')==pair and r.get('stage')=='peer'
            and (i>=first or r.get('call_id') in ids) and r.get('outcome') not in transport.UNCHARGED]
    used={};counts={}
    for r in chosen:
        actor=r['actor'];seconds=r.get('seconds')
        if type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<0:raise ValueError('invalid carried peer time')
        used[actor]=used.get(actor,0)+seconds;counts[actor]=counts.get(actor,0)+1
    return used,counts
