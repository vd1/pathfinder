"""Drained Pilot 15 copy; no real model execution or live pilot writes."""
import hashlib,json,os,shutil,tempfile,runpy
from pathlib import Path
from pathfinder import config,budget_reservation as br,budget_group as bg,orphan_recovery as orphan,research,transport,coordinator,stub,cli,freeze
source=Path('/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-15');out=Path(__file__).resolve().parent
call='a19a17a5367243c195b33e398b52ecf0'
def sha(p):return 'symlink:'+os.readlink(p) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(p):return {str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file() or f.is_symlink()}
before=inventory(source);live=config.load(source/'runs/pair-4')
rows=[]
for r in (source/'runs').glob('pair-*'):
 for row in transport.receipts(config.load(r)):
  if row.get('stage')=='consolidate' and row.get('outcome')=='completed':rows.append({k:row.get(k) for k in ('call_id','input_tokens','output_tokens','seconds')})
assert len(rows)==19 and max(x['input_tokens'] for x in rows)==692362 and max(x['output_tokens'] for x in rows)==24598
rationale='Explicit uncertainty estimate: 2000000 input and 75000 output tokens, rounded above twice maxima among 19 completed Pilot 15 consolidation receipts (692362 input,24598 output). Failed call lasted607.3 seconds, versus completed maximum590.9. Historical usage is only a heuristic, not measured usage or a proven upper bound; actual aggregate cap compliance remains uncertified.'
p=br.propose(live,call,2000000,75000,rationale,policy=br.SERVED_EXTENSION)
(out/'proposal.json').write_text(json.dumps(p,indent=2)+'\n');(out/'estimate-basis.json').write_text(json.dumps(rows,indent=2)+'\n')
(out/'approval-template.json').write_text(json.dumps(dict(proposal_sha256=br.digest(p),approved=False,accept_unknown_usage=False,accept_uncertified_actual_total=False,approved_by='',approved_at='',authority=''),indent=2)+'\n')
installer=runpy.run_path(str(out/'repin.py'));snap=installer['snapshot'](source,out/'proposal.json',[4,5,6]);(out/'migration-snapshot.json').write_text(json.dumps(snap,indent=2)+'\n')
root=Path(tempfile.mkdtemp(prefix='atlas-p15-served-',dir='/private/tmp'))/'pilot';shutil.copytree(source,root,symlinks=True)
def approval(p):return dict(proposal_sha256=br.digest(p),approved=True,accept_unknown_usage=True,accept_uncertified_actual_total=True,approved_by='OFFLINE FIXTURE',approved_at='2026-11-02T00:00:00Z',authority='Synthetic test only; no live approval')
def pin(group):
 for r in (root/'runs').glob('pair-*'):
  f=r/'campaign.json';raw=json.loads(f.read_text());raw['parent']='../..';raw['budget_group']=dict(manifest=str(group),sha256=sha(group));f.write_text(json.dumps(raw))
# Recreate the two existing approvals on copied, rebased evidence only.
oldpath=Path(live.raw['budget_group']['manifest']);olddoc=json.loads(oldpath.read_text())
group=root/'operator/budget-group.json';doc=json.loads(group.read_text());doc['campaigns']=[str(root/'runs'/Path(x).name) for x in doc['campaigns']];group.write_text(json.dumps(doc));pin(group)
c=config.load(root/'runs/pair-4');first=olddoc['reservations'][0]['proposal'];q=br.propose(c,first['call_id'],**first['reservation'],rationale='OFFLINE inherited unserved',policy=br.UNSERVED_POLICY)
v2=root/'operator/copy-v2.json';br.write_new(v2,br.approved_manifest(q,approval(q)));pin(v2)
c=config.load(root/'runs/pair-4');second=olddoc['reservations'][1]['proposal'];ocall=second['call_id'];archive=c.path(f'orphan-recoveries/{ocall}.json');s=json.loads(archive.read_text());s['snapshot']['root']=str(c.root);s['sha256']=orphan.digest(s['snapshot']);archive.write_text(json.dumps(s))
# The host-origin orphan row alone must rebind the copied root, never a provider receipt.
lines=c.path('receipts.jsonl').read_bytes().splitlines(keepends=True);lines=[(json.dumps(orphan._receipt(s['snapshot']),sort_keys=True)+'\n').encode() if json.loads(x).get('call_id')==ocall else x for x in lines];c.path('receipts.jsonl').write_bytes(b''.join(lines))
q=br.propose(c,ocall,**second['reservation'],rationale='OFFLINE inherited reboot',policy=br.ORPHAN_POLICY);v4=root/'operator/copy-v4.json';br.write_new(v4,br.approved_manifest(q,approval(q)));pin(v4)
c=config.load(root/'runs/pair-4');q=br.propose(c,call,2000000,75000,rationale,policy=br.SERVED_EXTENSION);qp=root/'operator/copy-proposal.json';br.write_new(qp,q)
cs=installer['snapshot'](root,qp,[4,5,6]);sp=root/'operator/copy-snapshot.json';br.write_new(sp,cs)
manifest=root/'operator/copy-v5.json';br.write_new(manifest,br.approved_manifest(q,approval(q)))
receipts={n:(root/f'runs/pair-{n}/receipts.jsonl').read_bytes() for n in range(1,7)}
threads={n:inventory(root/f'runs/pair-{n}/threads') for n in range(1,7)}
configs={n:json.loads((root/f'runs/pair-{n}/campaign.json').read_text()) for n in range(1,7)}
state=json.loads((c.thread_dir('Q001-P002')/'status.json').read_text());assert state['round']==5 and state['stage']=='consolidate'
assert not (c.thread_dir('Q001-P002')/'consolidation'/f"round-5-repair-{state.get('repairs',0)}.json").exists()
assert bg.report(c)['refusal'];result=installer['apply'](manifest,sp);assert result['validated_stops_to_clear']==[str(c.root)]
report=bg.report(config.load(c.root));assert report['refusal'] is None and not report['actual_total_certified']
for n in range(1,7):
 raw=json.loads((root/f'runs/pair-{n}/campaign.json').read_text());raw['budget_group']=configs[n]['budget_group'];assert raw==configs[n]
 assert inventory(root/f'runs/pair-{n}/threads')==threads[n]
assert cli.main(['--root',str(c.root),'stop','--clear']) in (None,0)
note=(c.thread_dir('Q001-P002')/'Q001-P002.tex').read_text();ledger=(c.thread_dir('Q001-P002')/'ledger.jsonl').read_bytes();calls=[]
def execute(c,r):
 assert c.root.is_relative_to(root) and bg.report(c)['refusal'] is None
 calls.append((c.root.name,r.stage,r.timeout))
 if c.root.name=='pair-4':
  assert r.stage in ('consolidate','verify')
  s=json.loads((c.thread_dir('Q001-P002')/'status.json').read_text());assert s['round']==5 and s.get('repairs')==state.get('repairs') and s.get('repair')==state.get('repair')
  if r.stage=='consolidate':assert r.timeout==3600
 if r.stage=='verify':text='{"decision":"PAUSE","score":4,"reason":"OFFLINE fixture only"}'
 elif r.stage=='consolidate':text=note
 elif r.stage=='peer':text=stub.reply(c,r)
 else:raise AssertionError(r.stage)
 return dict(text=text,error=None,transport_failed=False,session='offline',seconds=0)
transport.execute=execute
result=coordinator.run(root/'schedule.json',interval=.01,heartbeat=.01,accept_change='OFFLINE served-capacity approved migration')
assert result['status']=='complete',result
assert [(x[0],x[1]) for x in calls]==[('pair-4','consolidate'),('pair-4','verify')]+[(f'pair-{n}',s) for n in (5,6) for s in ('peer','consolidate','verify')]
for n in range(1,4):assert inventory(root/f'runs/pair-{n}/threads')==threads[n]
for path,h in threads[4].items():
 if 'ada' in Path(path).parts:assert sha(root/'runs/pair-4/threads'/path)==h
assert (c.thread_dir('Q001-P002')/'ledger.jsonl').read_bytes().startswith(ledger)
for n,data in receipts.items():assert (root/f'runs/pair-{n}/receipts.jsonl').read_bytes()==data
assert inventory(source)==before
proof=dict(copy=str(root),calls=calls,model_calls=0,original_files_preserved=len(before),proposal_sha256=br.digest(p),live_bindings=before,group_report=report,copy_rebase='Prior approvals recreated synthetically for copied roots. Host orphan row rebound only on copy; all provider receipts exact.',engine=str(Path(research.__file__).resolve()))
(out/'copy-result.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items() if k not in ('live_bindings','group_report')},indent=2))
