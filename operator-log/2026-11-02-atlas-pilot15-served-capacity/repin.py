"""Inert migration snapshot and approved group-only installation under idle ownership."""
import argparse,contextlib,fcntl,hashlib,json,os
from pathlib import Path
from pathfinder import budget_reservation as br,config,health

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(pilot,proposal,pairs):
 pilot=Path(pilot).resolve();p=json.loads(Path(proposal).read_text());br._validate(p)
 assert p['policy']==br.SERVED_EXTENSION
 roots=[Path(x) for x in p['scope']['campaigns']]
 assert all(r.parent==pilot/'runs' for r in roots)
 chosen=[pilot/f'runs/pair-{n}' for n in pairs];assert chosen and len(set(chosen))==len(chosen) and all(r in roots for r in chosen)
 assert Path(p['root']) in chosen
 files={};stops=[]
 for root in [pilot,*roots]:
  assert not list((root/'active-calls').glob('*.json')),'Active calls remain'
  runner=health.read(root/'runner.json') or {}
  assert not health.alive(runner.get('pid')),'Runner is alive'
  if (root/'runner.json').exists():files[str(root/'runner.json')]=sha(root/'runner.json')
  marker=root/'stop.json'
  if marker.exists():
   assert root in chosen,'Stop outside migration scope'
   reason=json.loads(marker.read_text())['reason']
   assert reason=='operator' or reason==f"budget: shared group has unknown or invalid input_tokens in {p['root']}",'Unexpected stop'
   files[str(marker)]=sha(marker);stops.append(str(root))
 for root in roots:
  for name in ('campaign.json','receipts.jsonl'):
   if (root/name).exists():files[str(root/name)]=sha(root/name)
 for root in chosen:
  cfg=json.loads((root/'campaign.json').read_text())
  assert cfg['budget_group']==dict(manifest=p['parent_manifest'],sha256=p['parent_sha256'])
  for f in (root/'threads').rglob('*'):
   if f.is_file() and not f.is_symlink():files[str(f)]=sha(f)
 return dict(version=1,pilot=str(pilot),proposal_sha256=br.digest(p),roots=[str(x) for x in chosen],files=files,stops=stops)

def apply(manifest,saved):
 manifest=Path(manifest).resolve();doc=json.loads(manifest.read_text());br.records(doc);s=json.loads(Path(saved).read_text());p=doc['reservations'][-1]['proposal']
 assert doc['version']==5 and p['policy']==br.SERVED_EXTENSION and s['proposal_sha256']==br.digest(p)
 pilot=Path(s['pilot']);old=Path(p['parent_manifest']);roots=[Path(x) for x in doc['campaigns']]
 with contextlib.ExitStack() as stack:
  for root in [pilot,*roots]:
   c=type('Root',(),{'root':root,'path':lambda self,n:self.root/n})();stack.enter_context(health.owner(c))
  for path in (old,manifest):
   f=stack.enter_context(Path(str(path)+'.lock').open('a+'));fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  assert all(not list((r/'active-calls').glob('*.json')) for r in roots)
  for path,h in s['files'].items():assert sha(Path(path))==h,f'Changed migration binding: {path}'
  for root in [pilot,*roots]:assert ((root/'stop.json').exists())==(str(root) in s['stops']),'Stop changed'
  pending=[]
  for name in s['roots']:
   root=Path(name);assert root in roots
   path=root/'campaign.json';raw=path.read_bytes();cfg=json.loads(raw)
   assert cfg['budget_group']==dict(manifest=str(old),sha256=p['parent_sha256'])
   backup=root/f"campaign.before-served-{p['call_id']}.json";assert not backup.exists(),'Migration already attempted'
   cfg['budget_group']=dict(manifest=str(manifest),sha256=sha(manifest));config.campaign_from(root,cfg)
   pending.append((path,backup,raw,cfg))
  for path,backup,raw,cfg in pending:
   with backup.open('xb') as f:f.write(raw)
  for path,backup,raw,cfg in pending:
   temp=path.with_name('campaign.served-pending.json')
   with temp.open('x') as f:json.dump(cfg,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
   os.replace(temp,path)
 return dict(repinned=s['roots'],validated_stops_to_clear=s['stops'],model_calls=0)
if __name__=='__main__':
 a=argparse.ArgumentParser();sub=a.add_subparsers(dest='action',required=True)
 p=sub.add_parser('snapshot');p.add_argument('--pilot',required=True);p.add_argument('--proposal',required=True);p.add_argument('--pairs',type=int,nargs='+',required=True);p.add_argument('--out',required=True)
 p=sub.add_parser('apply');p.add_argument('--manifest',required=True);p.add_argument('--snapshot',required=True)
 n=a.parse_args()
 if n.action=='snapshot':br.write_new(n.out,snapshot(n.pilot,n.proposal,n.pairs));print(n.out)
 else:print(json.dumps(apply(n.manifest,n.snapshot),indent=2))
