"""Offline actual Atlas copy recovery; every provider call replaced with a local fixture."""
from pathlib import Path
import hashlib,json,shutil,tempfile,os
from pathfinder import config,reopen_recovery,research,transport
source=Path('/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-6/runs/pair-1')
snapshot=source.parents[1]/'operator/pair-1-pre-reopen-snapshot/Q001-P002.tex'
pair='Q001-P002'
sha=lambda p: "symlink:"+os.readlink(p) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest()
def inv(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() or p.is_symlink()}
before=inv(source)
root=Path(tempfile.mkdtemp(prefix='atlas-reopen-copy-',dir='/private/tmp'))/'campaign'
shutil.copytree(source,root,symlinks=True)
local_snapshot=root.parent/'judged.tex';shutil.copyfile(snapshot,local_snapshot)
# The copied root is intentionally outside the live budget group. No transport
# admission is invoked: every model boundary below is replaced by a fixture.
c=config.campaign_from(root,json.loads((root/'campaign.json').read_text()))
plan=reopen_recovery.recover(c,pair,local_snapshot,'Offline proof of same-grant recovery')
result=reopen_recovery.recover(c,pair,local_snapshot,'Offline proof of same-grant recovery',apply=True,expected=plan['sha256'])
d=c.thread_dir(pair);archive=Path(result['custody'])/'before'
assert all(sha(archive/name)==digest for name,digest in plan['files'].items())
assert (d/f'{pair}.tex').read_bytes()==local_snapshot.read_bytes()
seen=[]
def execute(c,r):
    seen.append({'stage':r.stage,'prompt_sha256':hashlib.sha256(r.prompt.encode()).hexdigest()})
    if r.stage=='consolidate':
        assert plan['review']['action'] in r.prompt
        text=local_snapshot.read_text()+'\n% Offline recovery fixture only\n'
    elif r.stage=='verify':
        text=json.dumps({'decision':'ITERATE','reason':'offline sentinel','action':'not a live scientific review'})
    else:raise AssertionError(r.stage)
    return {'text':text,'transport_failed':False,'error':None,'session':'offline-fixture','seconds':0}
transport.execute=execute
assert research.run_thread(c,pair)=='PAUSE-ON-ITERATE'
assert [r['stage'] for r in seen]==['consolidate','verify']
assert research.status(c,pair)['grant'] is None
assert (d/f'{pair}.reopen.json').read_bytes()==(archive/f'{pair}.reopen.json').read_bytes()
assert all(sha(archive/name)==digest for name,digest in plan['files'].items())
assert sha(c.path('receipts.jsonl'))==plan['receipts_sha256']
assert before==inv(source)
report=dict(engine=str(Path(research.__file__).resolve()),copy=str(root),calls=seen,real_model_calls=0,
            original_files_preserved=len(before),archived_thread_files=len(plan['files']),
            original_note_sha256=plan['snapshot_sha256'],void_calls_preserved=plan['retained_call_ids'],
            same_grant_preserved=True,one_verdict=True,original_bindings=before)
Path(__file__).with_name('copy-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='original_bindings'},indent=2))
