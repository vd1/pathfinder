"""Actual Pilot 12 evidence, frozen runtime, offline model boundaries only."""
import hashlib,json,os,shutil,tempfile
from pathlib import Path
from pathfinder import config,budget_reservation as br,budget_group as bg,research,transport,coordinator,runner,cli,freeze,stub
source=Path('/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-12')
out=Path(__file__).resolve().parent
call='cce0c93c4a6b43b48ae584ace0bec737'
def sha(p):return 'symlink:'+os.readlink(p) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(p):return {str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file() or f.is_symlink()}
before=inventory(source)
engine=Path(research.__file__).resolve().parent.parent
verified=freeze.verify(engine,Path('/Users/v/Code_2026/pathfinder'))
assert verified['status']=='verified',verified
# Inert original-root proposal. No live writes, no authority inferred.
live=config.load(source/'runs/pair-5')
rationale='Completed result 2409522 input / 57199 output plus explicitly uncertain init-tail estimate 2500000 input / 25000 output. No assistant activity was observed, but in-flight usage is not certified zero. Estimate is not a proven bound; actual total cap compliance remains uncertified.'
p=br.propose(live,call,4909522,82199,rationale,policy=br.CLAUDE_INIT_POLICY)
(out/'proposal.json').write_text(json.dumps(p,indent=2)+'\n')
(out/'approval-template.json').write_text(json.dumps(dict(proposal_sha256=br.digest(p),approved=False,accept_unknown_usage=False,accept_uncertified_actual_total=False,approved_by='',approved_at='',authority=''),indent=2)+'\n')
root=Path(tempfile.mkdtemp(prefix='atlas-p12-init-',dir='/private/tmp'))/'pilot'
shutil.copytree(source,root,symlinks=True)
group=root/'operator/budget-group.json';doc=json.loads(group.read_text());doc['campaigns']=[str(root/'runs'/Path(x).name) for x in doc['campaigns']];group.write_text(json.dumps(doc))
for r in sorted((root/'runs').glob('pair-*')):
 f=r/'campaign.json';raw=json.loads(f.read_text());raw['parent']='../..';raw['budget_group']={'manifest':str(group),'sha256':sha(group)};f.write_text(json.dumps(raw))
# Reconstruct the first approval on copies only after rebasing their roots.
# The original approved manifest remains byte-identical at its live path.
first=config.load(root/'runs/pair-1')
fp=br.propose(first,'6e55ceedf4814fd4948d57d68841a19c',7382906,103455,'OFFLINE prior-reservation fixture',policy=br.CLAUDE_TAIL_POLICY)
fa=dict(proposal_sha256=br.digest(fp),approved=True,accept_unknown_usage=True,accept_uncertified_actual_total=True,approved_by='OFFLINE',approved_at='test',authority='Synthetic copy fixture only')
v2=root/'operator/copy-v2.json';br.write_new(v2,br.approved_manifest(fp,fa));v2before=v2.read_bytes()
for n in range(1,7):
 f=root/f'runs/pair-{n}/campaign.json';raw=json.loads(f.read_text());raw['budget_group']=dict(manifest=str(v2),sha256=sha(v2));f.write_text(json.dumps(raw))
c=config.load(root/'runs/pair-5');assert 'unknown' in bg.report(c)['refusal']
p2=br.propose(c,call,4909522,82199,rationale,policy=br.CLAUDE_INIT_POLICY)
ap=dict(proposal_sha256=br.digest(p2),approved=True,accept_unknown_usage=True,accept_uncertified_actual_total=True,approved_by='OFFLINE FIXTURE',approved_at='2026-10-31T00:00:00Z',authority='Synthetic test only, no live approval')
manifest=root/'operator/reserved.json';br.write_new(manifest,br.approved_manifest(p2,ap))
# Rebase only copied stop-marker root text for installation preflight.
for n in (5,6):
 f=root/f'runs/pair-{n}/stop.json';f.write_text(f.read_text().replace(str(source),str(root)))
import runpy
repin=runpy.run_path(str(out/'repin.py'))['apply']
repin(root,manifest)
assert v2.read_bytes()==v2before
assert json.loads(manifest.read_text())['reservations'][0]==json.loads(v2before)['reservations'][0]
report=bg.report(config.load(root/'runs/pair-5'));assert report['refusal'] is None and report['actual_total_certified'] is False
for n in (5,6):assert cli.main(['--root',str(root/f'runs/pair-{n}'),'stop','--clear']) in (None,0)
receipts={n:(root/f'runs/pair-{n}/receipts.jsonl').read_bytes() for n in range(1,7)}
oldnote=root/'runs/pair-5/threads/Q001-P002/Q001-P002.tex';note=oldnote.read_bytes()
peer_dir=root/'runs/pair-5/threads/Q001-P002/ada'
peer_files=inventory(peer_dir)
ledger=root/'runs/pair-5/threads/Q001-P002/ledger.jsonl';ledger_before=ledger.read_bytes()
assert json.loads(ledger_before.splitlines()[-1])['seq']==52
assert json.loads(ledger_before.splitlines()[-1])['seen']==50
assert research.Ledger(ledger).latest_substantive()==51
assert not research.Ledger(ledger).ready(['ada'],after=46)
completed={n:inventory(root/f'runs/pair-{n}/threads') for n in range(1,5)}
calls=[]
def execute(c,r):
 assert Path(c.root).is_relative_to(root)
 assert bg.report(c)['refusal'] is None
 calls.append((c.root.name,r.stage))
 if c.root.name=='pair-5':
  assert c.allowances['peer_calls']==1 and c.allowances['peer_seconds']==2937.4, c.allowances
  if r.stage=='peer':assert r.timeout<=2967.4, r.timeout
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
assert calls[:3]==[('pair-5','peer'),('pair-5','consolidate'),('pair-5','verify')],calls
assert calls[3:]==[(f'pair-{n}',s) for n in (6,) for s in ('peer','consolidate','verify')],calls
assert oldnote.read_bytes()==note
assert all((root/f'runs/pair-{n}/receipts.jsonl').read_bytes()==data for n,data in receipts.items())
assert inventory(peer_dir)==peer_files
assert ledger.read_bytes().startswith(ledger_before)
assert all(inventory(root/f'runs/pair-{n}/threads')==v for n,v in completed.items())
assert inventory(source)==before
proof=dict(engine=verified,copy=str(root),calls=calls,original_files_preserved=len(before),proposal_sha256=br.digest(p),group_report=report,live_bindings=before,real_model_calls=0,scope='Coordinator, runner, provenance and research state machine real; model boundary replaced by fixtures; synthetic approval on copy only.')
(out/'copy-result.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({k:v for k,v in proof.items() if k not in ('live_bindings','engine','group_report')},indent=2))
