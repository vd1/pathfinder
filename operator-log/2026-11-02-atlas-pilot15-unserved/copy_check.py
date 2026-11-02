"""Actual Pilot 15 evidence, frozen runtime, offline model boundaries only."""
import hashlib,json,os,shutil,tempfile
from pathlib import Path
from pathfinder import config,budget_reservation as br,budget_group as bg,research,transport,coordinator,runner,cli,freeze,stub
source=Path('/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-15')
out=Path(__file__).resolve().parent
call='12cb403b779c482db558ee8a5e78ec1c'
def sha(p):return 'symlink:'+os.readlink(p) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(p):return {str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file() or f.is_symlink()}
before=inventory(source)
engine=Path(research.__file__).resolve().parent.parent
verified=freeze.verify(engine,Path('/Users/v/Code_2026/pathfinder'))
assert verified['status']=='verified',verified
# Inert original-root proposal. No live writes, no authority inferred.
live=config.load(source/'runs/pair-4')
rationale='Explicit small uncertainty allowance of 100000 input / 1000 output for the retained capacity stream with no observed model-produced item. CLI warning is not model work; actual provider usage is unreported, not certified zero. Estimate is not a proven upper bound; actual cap compliance remains uncertified.'
p=br.propose(live,call,100000,1000,rationale,policy=br.UNSERVED_POLICY)
(out/'proposal.json').write_text(json.dumps(p,indent=2)+'\n')
(out/'approval-template.json').write_text(json.dumps(dict(proposal_sha256=br.digest(p),approved=False,accept_unknown_usage=False,accept_uncertified_actual_total=False,approved_by='',approved_at='',authority=''),indent=2)+'\n')
root=Path(tempfile.mkdtemp(prefix='atlas-p15-unserved-',dir='/private/tmp'))/'pilot'
shutil.copytree(source,root,symlinks=True)
group=root/'operator/budget-group.json';doc=json.loads(group.read_text());doc['campaigns']=[str(root/'runs'/Path(x).name) for x in doc['campaigns']];group.write_text(json.dumps(doc))
for r in sorted((root/'runs').glob('pair-*')):
 f=r/'campaign.json';raw=json.loads(f.read_text());raw['parent']='../..';raw['budget_group']={'manifest':str(group),'sha256':sha(group)};f.write_text(json.dumps(raw))
c=config.load(root/'runs/pair-4');assert 'unknown' in bg.report(c)['refusal']
p2=br.propose(c,call,100000,1000,rationale,policy=br.UNSERVED_POLICY)
ap=dict(proposal_sha256=br.digest(p2),approved=True,accept_unknown_usage=True,accept_uncertified_actual_total=True,approved_by='OFFLINE FIXTURE',approved_at='2026-11-02T00:00:00Z',authority='Synthetic test only, no live approval')
manifest=root/'operator/reserved.json';br.write_new(manifest,br.approved_manifest(p2,ap))
# Rebase only copied stop-marker root text for installation preflight.
for n in (4,5,6):
 f=root/f'runs/pair-{n}/stop.json';f.write_text(f.read_text().replace(str(source),str(root)))
import runpy
repin=runpy.run_path(str(out/'repin.py'))['apply']
repin(root,manifest)
report=bg.report(config.load(root/'runs/pair-4'));assert report['refusal'] is None and report['actual_total_certified'] is False
for n in (4,5,6):assert cli.main(['--root',str(root/f'runs/pair-{n}'),'stop','--clear']) in (None,0)
receipts={n:(root/f'runs/pair-{n}/receipts.jsonl').read_bytes() for n in range(1,7)}
oldnote=root/'runs/pair-4/threads/Q001-P002/Q001-P002.tex';note=oldnote.read_bytes()
preserved={n:inventory(root/f'runs/pair-{n}/threads') for n in range(1,4)}
p4thread=root/'runs/pair-4/threads/Q001-P002'
p4kept={str(f.relative_to(p4thread)):sha(f) for f in p4thread.rglob('*') if f.is_file() and ('ada' in f.relative_to(p4thread).parts or 'consolidation' in f.relative_to(p4thread).parts or f.name=='ledger.jsonl')}
calls=[]
def execute(c,r):
 assert Path(c.root).is_relative_to(root)
 assert bg.report(c)['refusal'] is None
 calls.append((c.root.name,r.stage))
 if c.root.name=='pair-4':assert r.stage=='verify'
 if r.stage=='verify':text='{"decision":"PAUSE","score":4,"reason":"OFFLINE fixture; not a scientific verdict"}'
 elif r.stage=='consolidate':text=note.decode()
 elif r.stage=='peer':
  assert Path(r.cwd).resolve().is_relative_to(root)
  text=stub.reply(c,r)
 else:raise AssertionError(r.stage)
 return dict(text=text,error=None,transport_failed=False,session='offline',seconds=0)
transport.execute=execute
result=coordinator.run(root/'schedule.json',interval=.01,heartbeat=.01,accept_change='OFFLINE reservation proof')
assert result['status']=='complete',result
assert calls==[('pair-4','verify')]+[(f'pair-{n}',s) for n in (5,6) for s in ('peer','consolidate','verify')],calls
assert oldnote.read_bytes()==note
assert all(sha(p4thread/f)==v for f,v in p4kept.items() if f!='ledger.jsonl')
assert (p4thread/'ledger.jsonl').read_bytes().startswith((source/'runs/pair-4/threads/Q001-P002/ledger.jsonl').read_bytes())
assert all((root/f'runs/pair-{n}/receipts.jsonl').read_bytes()==data for n,data in receipts.items())
assert all(inventory(root/f'runs/pair-{n}/threads')==inv for n,inv in preserved.items())
assert inventory(source)==before
proof=dict(engine=verified,copy=str(root),calls=calls,original_files_preserved=len(before),proposal_sha256=br.digest(p),group_report=report,live_bindings=before,real_model_calls=0,scope='Coordinator, runner, provenance and research state machine real; model boundary replaced by fixtures; synthetic approval on copy only.')
(out/'copy-result.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({k:v for k,v in proof.items() if k not in ('live_bindings','engine','group_report')},indent=2))
