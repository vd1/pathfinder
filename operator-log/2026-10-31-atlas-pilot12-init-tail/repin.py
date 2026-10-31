"""Operator-only configuration migration after real reservation approval; no state edits."""
import argparse,contextlib,fcntl,hashlib,json,os
from pathlib import Path
from pathfinder import budget_reservation as br,config,health

def apply(pilot,manifest):
    pilot=Path(pilot).resolve();manifest=Path(manifest).resolve()
    data=manifest.read_bytes();doc=json.loads(data)
    br.records(doc)  # validates real recorded approval and immutable source evidence
    proposal=doc['reservations'][1]['proposal'];old=Path(proposal['parent_manifest'])
    roots=[pilot/f'runs/pair-{n}' for n in range(1,7)]
    assert doc['campaigns']==[str(p) for p in roots]
    assert proposal['root']==str(roots[4])
    assert proposal['call_id']=='cce0c93c4a6b43b48ae584ace0bec737'
    assert proposal['reservation']==dict(input_tokens=4909522,output_tokens=82199)
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
            backup=root/'campaign.before-pilot12-init-reservation.json'
            assert not backup.exists(),'Migration already attempted; inspect before retry'
            cfg['budget_group']=dict(manifest=str(manifest),sha256=hashlib.sha256(data).hexdigest())
            if root == roots[4]:
                state=json.loads((root/'threads/Q001-P002/status.json').read_text())
                assert state['round']==6 and state['stage']=='peers' and state['status']=='stopped'
                rows=[json.loads(x) for x in (root/'receipts.jsonl').read_text().splitlines() if x.strip()]
                last_verify=max(i for i,r in enumerate(rows) if r.get('stage')=='verify' and r.get('outcome')=='completed')
                served=[r for r in rows[last_verify+1:] if r.get('stage')=='peer' and r.get('outcome') not in ('refused','launch failed','no session')]
                assert len(served)==1 and served[0]['call_id']==proposal['call_id'] and served[0]['seconds']==662.6
                assert cfg['allowances']['peer_calls']==2 and cfg['allowances']['peer_seconds']==3600
                # Resume the remaining original turn, not a fresh full in-memory peer allowance.
                cfg['allowances']['peer_calls']=1
                cfg['allowances']['peer_seconds']=2937.4
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
