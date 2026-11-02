"""Operator migration after evidence recovery and explicit reservation approval."""
import argparse,contextlib,fcntl,hashlib,json,os
from pathlib import Path
from pathfinder import budget_reservation as br,config,health,orphan_recovery
CALL='e7e55c64bf35432483adbf8803683cf3'
def apply(pilot,manifest):
 pilot=Path(pilot).resolve();manifest=Path(manifest).resolve();data=manifest.read_bytes();doc=json.loads(data)
 br.records(doc)
 assert doc['version']==4
 proposal=doc['reservations'][-1]['proposal'];old=Path(proposal['parent_manifest'])
 roots=[pilot/f'runs/pair-{n}' for n in range(1,7)]
 assert doc['campaigns']==[str(p) for p in roots] and proposal['root']==str(roots[3])
 assert proposal['call_id']==CALL and proposal['policy']==br.ORPHAN_POLICY
 assert not (pilot/'stop.json').exists(),'Unexpected stop requires separate diagnosis'
 with contextlib.ExitStack() as stack:
  for root in [pilot,*roots]:
   c=type('Root',(),{'root':root,'path':lambda self,n:self.root/n})();stack.enter_context(health.owner(c))
  for path in (old,manifest):
   stream=stack.enter_context(Path(str(path)+'.lock').open('a+'));fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
  assert all(not list((r/'active-calls').glob('*.json')) for r in roots)
  c=config.load(roots[3]);assert c.path(f'orphan-recoveries/{CALL}.json').exists()
  orphan_recovery.evidence_receipt(c,CALL)
  pending=[]
  for root in roots[3:]:
   assert not (root/'stop.json').exists(),'Unexpected stop requires separate diagnosis'
   path=root/'campaign.json';raw=path.read_bytes();cfg=json.loads(raw)
   assert cfg['budget_group']==dict(manifest=str(old),sha256=proposal['parent_sha256'])
   backup=root/'campaign.before-pilot15-reboot.json';assert not backup.exists(),'Migration already attempted; inspect before retry'
   cfg['budget_group']=dict(manifest=str(manifest),sha256=hashlib.sha256(data).hexdigest())
   config.campaign_from(root,cfg);pending.append((path,backup,raw,cfg))
  for path,backup,raw,cfg in pending:
   with backup.open('xb') as f:f.write(raw)
  for path,backup,raw,cfg in pending:
   temp=path.with_name('campaign.reboot-pending.json')
   with temp.open('x') as f:json.dump(cfg,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
   os.replace(temp,path)
 return dict(repinned=[str(r) for r in roots[3:]],manifest=str(manifest),model_calls=0)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--pilot',required=True);ap.add_argument('--manifest',required=True)
 a=ap.parse_args();print(json.dumps(apply(a.pilot,a.manifest),indent=2))
