"""Operator-only configuration migration after real reservation approval; no state edits."""
import argparse,contextlib,fcntl,hashlib,json,os
from pathlib import Path
from pathfinder import budget_reservation as br,config,health

def apply(pilot,manifest):
    pilot=Path(pilot).resolve();manifest=Path(manifest).resolve()
    data=manifest.read_bytes();doc=json.loads(data)
    br.records(doc)  # validates real recorded approval and immutable source evidence
    proposal=doc['reservations'][0]['proposal'];old=Path(proposal['parent_manifest'])
    roots=[pilot/f'runs/pair-{n}' for n in range(1,7)]
    assert doc['campaigns']==[str(p) for p in roots]
    assert proposal['root']==str(roots[4])
    assert proposal['call_id']=='417a84f1b21c48be8c0beaf64580203f'
    assert proposal['reservation']==dict(input_tokens=2500000,output_tokens=25000)
    assert not (pilot/'stop.json').exists(),'Unrelated parent stop requires diagnosis'
    with contextlib.ExitStack() as stack:
        for root in [pilot,*roots]:
            c=type('Root',(),{'root':root,'path':lambda self,n:self.root/n})()
            stack.enter_context(health.owner(c))
        for path in (old,manifest):
            stream=stack.enter_context(Path(str(path)+'.lock').open('a+'))
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert all(not list((r/'active-calls').glob('*.json')) for r in roots)
        pending=[]
        for root in roots[4:]:
            marker=json.loads((root/'stop.json').read_text())
            assert marker['reason']==f'budget: shared group has unknown or invalid input_tokens in {roots[4]}'
            path=root/'campaign.json';raw=path.read_bytes();cfg=json.loads(raw)
            assert cfg['budget_group']==dict(manifest=str(old),sha256=proposal['parent_sha256'])
            backup=root/'campaign.before-pilot11-reservation.json'
            assert not backup.exists(),'Migration already attempted; inspect before retry'
            cfg['budget_group']=dict(manifest=str(manifest),sha256=hashlib.sha256(data).hexdigest())
            # Validate the complete changed config before writing either campaign.
            config.campaign_from(root,cfg)
            pending.append((path,backup,raw,cfg))
        for path,backup,raw,cfg in pending:
            with backup.open('xb') as f:f.write(raw)
        for path,backup,raw,cfg in pending:
            temp=path.with_name('campaign.reservation-pending.json')
            with temp.open('x') as f:json.dump(cfg,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
            os.replace(temp,path)
    return dict(repinned=[str(r) for r in roots[4:]],manifest=str(manifest),stops_cleared=False,model_calls=0)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--pilot',required=True);ap.add_argument('--manifest',required=True)
    args=ap.parse_args();print(json.dumps(apply(args.pilot,args.manifest),indent=2))
