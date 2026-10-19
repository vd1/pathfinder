from pathlib import Path
import shutil,json,tempfile
from pathfinder import config,pce,pce_recovery,pce_evidence,stub
source=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2')
target=Path(tempfile.mkdtemp(prefix='batch2-upgrade-',dir='/private/tmp'))
for name in ('campaign.json','Q.jsonl','P.jsonl','shortlist.json'):
 if (source/name).exists():shutil.copy(source/name,target/name)
c=config.load(target)
report={}
for pair,manifest in [('Q040-P030','q040-projection.json')]:
 src=source/'threads'/pair;dst=target/'threads'/pair;dst.mkdir(parents=True)
 for p in src.iterdir():
  if p.is_file() and p.suffix in ('.json','.jsonl','.tex'):shutil.copy(p,dst/p.name)
 for name in ('edited','inputs'):shutil.copytree(src/name,dst/name)
 for ledger in src.glob('branches/*/ledger.jsonl'):
  p=dst/ledger.relative_to(src);p.parent.mkdir(parents=True,exist_ok=True);shutil.copy(ledger,p)
 manifest=Path('/Users/v/Code_2026/pathfinder/operator-log/2026-10-19-batch2-evidence')/manifest if manifest else None
 if manifest:
  for row in pce_evidence.read(manifest)['include']:
   p=dst/row['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy(src/row['path'],p)
 before=pce_recovery.hashes(dst/'edited');science=(dst/'status.json').read_bytes()
 action=json.loads(Path('/Users/v/Code_2026/pathfinder/operator-log/2026-10-20-model-scope/q040-action.json').read_text())['prepare_argv']
 reason=action[action.index('--reason')+1]
 root=pce_recovery.grant(c,pair,'ensemble-scope-copy',1,1,reason,evidence=manifest)
 calls=[]
 def dispatch(campaign,pair_id,role,prompt,seconds=None):
  calls.append({'role':role,'chars':len(prompt)})
  return {'role':role,'outcome':'completed','text':stub.pce_reply(campaign,role,prompt)}
 pce._dispatch=dispatch
 result=pce.run(c,pair)
 assert result['status']=='accepted' and len(calls)==5
 after=pce_recovery.hashes(dst/'edited')
 assert all(after[k]==v for k,v in before.items() if k!='pce-active.json')
 assert science==(dst/'status.json').read_bytes()
 report[pair]={'status':result['status'],'calls':calls,'old_artifacts_preserved':True,'science_preserved':True}
print(json.dumps({'copy':str(target),'results':report},indent=2))
