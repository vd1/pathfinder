"""Pilot 16 first reservation on a temporary copy, all model execution stubbed."""
import hashlib,json,os,shutil,tempfile,runpy
from pathlib import Path
from pathfinder import config,budget_reservation as br,budget_group as bg,research,transport,coordinator,stub,cli,served_capacity
source=Path('/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-16');out=Path(__file__).resolve().parent
call='b883dfb6c21e49329b07f1e1f8d6c6d6'
def sha(p):return 'symlink:'+os.readlink(p) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(p):return {str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file() or f.is_symlink()}
before=inventory(source);live=config.load(source/'runs/pair-3')
rationale='Explicit uncertain reservation of 15000000 input and 150000 output tokens. Among 11 completed Pilot 16 peer calls, maxima were 6105086 input and 63653 output; both proposed amounts exceed twice those maxima, rounded upward. Scaling the fastest observed input rate to this 1673.4-second failed call gives approximately 5501055 input tokens. These comparisons are heuristic, not measured usage or a proven upper bound; actual aggregate cap compliance remains uncertified.'
p=br.propose(live,call,15000000,150000,rationale,policy=br.POLICY);basis=served_capacity.evidence(live.root,p['receipt'])
(out/'proposal.json').write_text(json.dumps(p,indent=2)+'\n');(out/'journal-validation.json').write_text(json.dumps(basis,indent=2)+'\n')
(out/'approval-template.json').write_text(json.dumps(dict(proposal_sha256=br.digest(p),approved=False,accept_unknown_usage=False,accept_uncertified_actual_total=False,approved_by='',approved_at='',authority=''),indent=2)+'\n')
installer=runpy.run_path(str(out/'repin.py'));snap=installer['snapshot'](source,out/'proposal.json',[3,4,5,6]);(out/'migration-snapshot.json').write_text(json.dumps(snap,indent=2)+'\n')
root=Path(tempfile.mkdtemp(prefix='atlas-p16-first-',dir='/private/tmp'))/'pilot';shutil.copytree(source,root,symlinks=True)
def approval(p):return dict(proposal_sha256=br.digest(p),approved=True,accept_unknown_usage=True,accept_uncertified_actual_total=True,approved_by='OFFLINE FIXTURE',approved_at='2026-11-03T00:00:00Z',authority='Synthetic test only; no live approval')
group=root/'operator/budget-group.json';doc=json.loads(group.read_text());assert doc['version']==1;doc['campaigns']=[str(root/'runs'/Path(x).name) for x in doc['campaigns']];group.write_text(json.dumps(doc))
for r in (root/'runs').glob('pair-*'):
 f=r/'campaign.json';raw=json.loads(f.read_text());raw['parent']='../..';raw['budget_group']=dict(manifest=str(group),sha256=sha(group));f.write_text(json.dumps(raw))
for n in (3,4,5,6):
 marker=root/f'runs/pair-{n}/stop.json';marker.write_text(marker.read_text().replace(str(source),str(root)))
c=config.load(root/'runs/pair-3');q=br.propose(c,call,15000000,150000,rationale,policy=br.POLICY);qp=root/'operator/copy-proposal.json';br.write_new(qp,q)
cs=installer['snapshot'](root,qp,[3,4,5,6]);sp=root/'operator/copy-snapshot.json';br.write_new(sp,cs)
manifest=root/'operator/copy-reserved.json';br.write_new(manifest,br.approved_manifest(q,approval(q)))
receipts={n:(root/f'runs/pair-{n}/receipts.jsonl').read_bytes() for n in range(1,7)}
threads={n:inventory(root/f'runs/pair-{n}/threads') for n in range(1,7)}
configs={n:json.loads((root/f'runs/pair-{n}/campaign.json').read_text()) for n in range(1,7)}
state=json.loads((c.thread_dir('Q001-P002')/'status.json').read_text());assert state['round']==4 and state['stage']=='peers'
assert not (c.thread_dir('Q001-P002')/'consolidation'/f"round-4-repair-{state.get('repairs',0)}.json").exists()
assert bg.report(c)['refusal'];result=installer['apply'](manifest,sp);assert result['validated_stops_to_clear']==[str(root/f'runs/pair-{n}') for n in (3,4,5,6)]
report=bg.report(config.load(c.root));assert report['refusal'] is None and not report['actual_total_certified']
for n in range(1,7):
 now=(root/f'runs/pair-{n}/campaign.json').read_bytes()
 raw=json.loads(now);raw['budget_group']=configs[n]['budget_group'];assert raw==configs[n]
 assert inventory(root/f'runs/pair-{n}/threads')==threads[n]
for n in (3,4,5,6):assert cli.main(['--root',str(root/f'runs/pair-{n}'),'stop','--clear']) in (None,0)
note=(c.thread_dir('Q001-P002')/'Q001-P002.tex').read_text();ledger=(c.thread_dir('Q001-P002')/'ledger.jsonl').read_bytes();calls=[]
def execute(c,r):
 assert c.root.is_relative_to(root) and bg.report(c)['refusal'] is None
 calls.append((c.root.name,r.stage,r.timeout))
 if c.root.name=='pair-3':
  s=json.loads((c.thread_dir('Q001-P002')/'status.json').read_text());assert s['round']==4 and s.get('repairs')==state.get('repairs') and s.get('repair')==state.get('repair')
  if r.stage=='peer':
   assert r.timeout==3630 and r.identity.endswith(':0')
   assert 'continues an existing thread' in r.prompt
   assert (r.cwd/'ada/round4-streaming.txt').read_bytes()==(source/'runs/pair-3/threads/Q001-P002/ada/round4-streaming.txt').read_bytes()
 if r.stage=='verify':text='{"decision":"PAUSE","score":4,"reason":"OFFLINE fixture only"}'
 elif r.stage=='consolidate':text=note
 elif r.stage=='peer':text=stub.reply(c,r)
 else:raise AssertionError(r.stage)
 return dict(text=text,error=None,transport_failed=False,session='offline',seconds=0)
transport.execute=execute
result=coordinator.run(root/'schedule.json',interval=.01,heartbeat=.01,accept_change='OFFLINE first capacity reservation and runtime migration')
assert result['status']=='complete',result
assert [(x[0],x[1]) for x in calls]==[(f'pair-{n}',s) for n in (3,4,5,6) for s in ('peer','consolidate','verify')]
for n in (1,2):assert inventory(root/f'runs/pair-{n}/threads')==threads[n]
for path,h in threads[3].items():
 if 'ada' in Path(path).parts or 'consolidation' in Path(path).parts:assert sha(root/'runs/pair-3/threads'/path)==h
assert (c.thread_dir('Q001-P002')/'ledger.jsonl').read_bytes().startswith(ledger)
for n,data in receipts.items():assert (root/f'runs/pair-{n}/receipts.jsonl').read_bytes()==data
assert inventory(source)==before
proof=dict(copy=str(root),calls=calls,model_calls=0,original_files_preserved=len(before),proposal_sha256=br.digest(p),live_bindings=before,group_report=report,copy_rebase='Only copied root paths, group pins and budget-marker paths rebased; synthetic approval only. All provider receipts exact.',engine=str(Path(research.__file__).resolve()))
(out/'copy-result.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items() if k not in ('live_bindings','group_report')},indent=2))
