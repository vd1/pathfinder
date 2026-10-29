"""Actual Pilot 12 evidence, frozen runtime, offline model boundaries only."""
import hashlib,json,os,shutil,tempfile
from pathlib import Path
from pathfinder import config,budget_reservation as br,budget_group as bg,research,transport,coordinator,runner,cli,freeze,stub
source=Path('/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-12')
out=Path(__file__).resolve().parent
call='6e55ceedf4814fd4948d57d68841a19c'
def sha(p):return 'symlink:'+os.readlink(p) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(p):return {str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file() or f.is_symlink()}
before=inventory(source)
engine=Path(research.__file__).resolve().parent.parent
verified=freeze.verify(engine,Path('/Users/v/Code_2026/pathfinder'))
assert verified['status']=='verified',verified
# Inert original-root proposal. No live writes, no authority inferred.
live=config.load(source/'runs/pair-1')
rationale='First completed turn 4882906 input / 78455 output plus an explicitly uncertain tail estimate 2500000 input / 25000 output. Tail message floor 160995 input / 7 output is not a final total; estimate is not a proven upper bound. Actual cap compliance remains uncertified.'
p=br.propose(live,call,7382906,103455,rationale,policy=br.CLAUDE_TAIL_POLICY)
(out/'proposal.json').write_text(json.dumps(p,indent=2)+'\n')
(out/'approval-template.json').write_text(json.dumps(dict(proposal_sha256=br.digest(p),approved=False,accept_unknown_usage=False,accept_uncertified_actual_total=False,approved_by='',approved_at='',authority=''),indent=2)+'\n')
root=Path(tempfile.mkdtemp(prefix='atlas-p12-tail-',dir='/private/tmp'))/'pilot'
shutil.copytree(source,root,symlinks=True)
group=root/'operator/budget-group.json';doc=json.loads(group.read_text());doc['campaigns']=[str(root/'runs'/Path(x).name) for x in doc['campaigns']];group.write_text(json.dumps(doc))
for r in sorted((root/'runs').glob('pair-*')):
 f=r/'campaign.json';raw=json.loads(f.read_text());raw['parent']='../..';raw['budget_group']={'manifest':str(group),'sha256':sha(group)};f.write_text(json.dumps(raw))
c=config.load(root/'runs/pair-1');assert 'unknown' in bg.report(c)['refusal']
p2=br.propose(c,call,7382906,103455,rationale,policy=br.CLAUDE_TAIL_POLICY)
ap=dict(proposal_sha256=br.digest(p2),approved=True,accept_unknown_usage=True,accept_uncertified_actual_total=True,approved_by='OFFLINE FIXTURE',approved_at='2026-10-29T00:00:00Z',authority='Synthetic test only, no live approval')
manifest=root/'operator/reserved.json';br.write_new(manifest,br.approved_manifest(p2,ap))
# Rebase only copied stop-marker root text for installation preflight.
for n in range(1,7):
 f=root/f'runs/pair-{n}/stop.json';f.write_text(f.read_text().replace(str(source),str(root)))
import runpy
repin=runpy.run_path(str(out/'repin.py'))['apply']
repin(root,manifest)
report=bg.report(config.load(root/'runs/pair-1'));assert report['refusal'] is None and report['actual_total_certified'] is False
for n in range(1,7):assert cli.main(['--root',str(root/f'runs/pair-{n}'),'stop','--clear']) in (None,0)
receipts={n:(root/f'runs/pair-{n}/receipts.jsonl').read_bytes() for n in range(1,7)}
oldnote=root/'runs/pair-1/threads/Q001-P002/Q001-P002.tex';note=oldnote.read_bytes()
peer_dir=root/'runs/pair-1/threads/Q001-P002/ada'
peer_files=inventory(peer_dir)
ledger=root/'runs/pair-1/threads/Q001-P002/ledger.jsonl';ledger_before=ledger.read_bytes()
assert json.loads(ledger_before.splitlines()[-1])['kind']=='ready'
calls=[]
def execute(c,r):
 assert Path(c.root).is_relative_to(root)
 assert bg.report(c)['refusal'] is None
 calls.append((c.root.name,r.stage))
 if c.root.name=='pair-1':assert r.stage in ('consolidate','verify')
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
assert calls[:2]==[('pair-1','consolidate'),('pair-1','verify')],calls
assert calls[2:]==[(f'pair-{n}',s) for n in range(2,7) for s in ('peer','consolidate','verify')],calls
assert oldnote.read_bytes()==note
assert all((root/f'runs/pair-{n}/receipts.jsonl').read_bytes()==data for n,data in receipts.items())
assert inventory(peer_dir)==peer_files
assert ledger.read_bytes().startswith(ledger_before)
assert inventory(source)==before
proof=dict(engine=verified,copy=str(root),calls=calls,original_files_preserved=len(before),proposal_sha256=br.digest(p),group_report=report,live_bindings=before,real_model_calls=0,scope='Coordinator, runner, provenance and research state machine real; model boundary replaced by fixtures; synthetic approval on copy only.')
(out/'copy-result.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({k:v for k,v in proof.items() if k not in ('live_bindings','engine','group_report')},indent=2))
