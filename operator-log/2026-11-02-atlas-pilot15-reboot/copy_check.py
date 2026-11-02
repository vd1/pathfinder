"""Actual Pilot 15 copy, canonical owner/coordinator, model boundary stubbed."""
import hashlib,json,os,shutil,tempfile,runpy
from pathlib import Path
from pathfinder import config,budget_reservation as br,budget_group as bg,orphan_recovery as o,research,transport,coordinator,stub,freeze
source=Path('/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-15');out=Path(__file__).resolve().parent
call='e7e55c64bf35432483adbf8803683cf3'
def sha(p):return 'symlink:'+os.readlink(p) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(p):return {str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file() or f.is_symlink()}
before=inventory(source);live=config.load(source/'runs/pair-4')
rationale='Explicit uncertain reservation of 15000000 input and 150000 output tokens. Among 19 completed Pilot 15 peer receipts the observed maxima were 7018735 input and 62714 output; each proposed amount exceeds twice that maximum, rounded upward. The interrupted call lasted at most 1568 seconds before boot, but usage is not reported. Historical comparisons are a heuristic, not a proven upper bound; actual aggregate cap compliance remains uncertified.'
p=br.propose(live,call,15000000,150000,rationale,policy=br.ORPHAN_POLICY)
(out/'proposal.json').write_text(json.dumps(p,indent=2)+'\n')
(out/'orphan-preview.json').write_text(json.dumps(o.inspect(live,call),indent=2)+'\n')
(out/'approval-template.json').write_text(json.dumps(dict(proposal_sha256=br.digest(p),approved=False,accept_unknown_usage=False,accept_uncertified_actual_total=False,approved_by='',approved_at='',authority=''),indent=2)+'\n')
root=Path(tempfile.mkdtemp(prefix='atlas-p15-reboot-',dir='/private/tmp'))/'pilot';shutil.copytree(source,root,symlinks=True)
def approval(p):return dict(proposal_sha256=br.digest(p),approved=True,accept_unknown_usage=True,accept_uncertified_actual_total=True,approved_by='OFFLINE FIXTURE',approved_at='2026-11-02T00:00:00Z',authority='Synthetic test only; no live approval')
# Rebase copied prior reservation through the same canonical validator.
group=root/'operator/budget-group.json';doc=json.loads(group.read_text());doc['campaigns']=[str(root/'runs'/Path(x).name) for x in doc['campaigns']];group.write_text(json.dumps(doc))
for r in (root/'runs').glob('pair-*'):
 f=r/'campaign.json';raw=json.loads(f.read_text());raw['parent']='../..';raw['budget_group']=dict(manifest=str(group),sha256=sha(group));f.write_text(json.dumps(raw))
c=config.load(root/'runs/pair-4');old_live=json.loads((source/'operator/budget-group-unserved-reserved.json').read_text())['reservations'][0]['proposal']
q=br.propose(c,old_live['call_id'],**old_live['reservation'],rationale='OFFLINE inherited reservation',policy=br.UNSERVED_POLICY)
old=root/'operator/rebased-unserved.json';br.write_new(old,br.approved_manifest(q,approval(q)))
for r in (root/'runs').glob('pair-*'):
 f=r/'campaign.json';raw=json.loads(f.read_text());raw['budget_group']=dict(manifest=str(old),sha256=sha(old));f.write_text(json.dumps(raw))
c=config.load(root/'runs/pair-4');snap=o.inspect(c,call)
assert snap['snapshot']['elapsed_upper_bound_seconds']==1568
receipts={n:(root/f'runs/pair-{n}/receipts.jsonl').read_bytes() for n in range(1,7)}
configs={n:json.loads((root/f'runs/pair-{n}/campaign.json').read_text()) for n in range(1,7)}
threads={n:inventory(root/f'runs/pair-{n}/threads') for n in range(1,7)}
q=br.propose(c,call,15000000,150000,rationale,policy=br.ORPHAN_POLICY)
assert bg.report(c)['refusal']
o.recover(c,call,apply=True,expected=snap['sha256']);assert bg.report(c)['refusal']
o.recover(c,call,apply=True,expected=snap['sha256'])
manifest=root/'operator/reboot-reserved.json';br.write_new(manifest,br.approved_manifest(q,approval(q)))
runpy.run_path(str(out/'repin.py'))['apply'](root,manifest)
c=config.load(root/'runs/pair-4');report=bg.report(c);assert report['refusal'] is None and not report['actual_total_certified']
for n in range(1,7):
 raw=json.loads((root/f'runs/pair-{n}/campaign.json').read_text());raw['budget_group']=configs[n]['budget_group'];assert raw==configs[n]
 assert inventory(root/f'runs/pair-{n}/threads')==threads[n]
assert o.peer_carry(c,'Q001-P002',snap['snapshot']['peer_phase'])==({'ada':1568},{'ada':1})
ledger=(c.thread_dir('Q001-P002')/'ledger.jsonl').read_bytes();note=(c.thread_dir('Q001-P002')/'Q001-P002.tex').read_text()
calls=[]
def execute(c,r):
 assert c.root.is_relative_to(root) and bg.report(c)['refusal'] is None
 calls.append((c.root.name,r.stage,r.timeout))
 if c.root.name=='pair-4' and r.stage=='peer':
  assert r.timeout==2062 and r.identity.endswith(':1')
  assert (r.cwd/'ada/round5.md').read_bytes()==(source/'runs/pair-4/threads/Q001-P002/ada/round5.md').read_bytes()
 if r.stage=='verify':text='{"decision":"PAUSE","score":4,"reason":"OFFLINE fixture only"}'
 elif r.stage=='consolidate':text=note
 elif r.stage=='peer':text=stub.reply(c,r)
 else:raise AssertionError(r.stage)
 return dict(text=text,error=None,transport_failed=False,session='offline',seconds=0)
transport.execute=execute
result=coordinator.run(root/'schedule.json',interval=.01,heartbeat=.01,accept_change='OFFLINE reboot accounting and engine proof')
assert result['status']=='complete',result
assert [(x[0],x[1]) for x in calls]==[(f'pair-{n}',s) for n in (4,5,6) for s in ('peer','consolidate','verify')],calls
for n in range(1,4):assert inventory(root/f'runs/pair-{n}/threads')==threads[n]
assert (c.thread_dir('Q001-P002')/'ledger.jsonl').read_bytes().startswith(ledger)
assert (c.thread_dir('Q001-P002')/'ada/round5.md').read_bytes()==(source/'runs/pair-4/threads/Q001-P002/ada/round5.md').read_bytes()
for n in range(1,7):
 data=(root/f'runs/pair-{n}/receipts.jsonl').read_bytes();assert data.startswith(receipts[n])
 assert n==4 or data==receipts[n]
assert inventory(source)==before
proof=dict(frozen_runtime=freeze.verify(Path(research.__file__).resolve().parent.parent,Path('/Users/v/Code_2026/pathfinder')),copy=str(root),calls=calls,model_calls=0,original_files_preserved=len(before),proposal_sha256=br.digest(p),orphan_snapshot_sha256=o.inspect(live,call)['sha256'],live_bindings=before,group_report=report)
(out/'copy-result.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items() if k not in ('live_bindings','group_report')},indent=2))
