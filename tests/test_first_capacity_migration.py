import hashlib,json,runpy
from pathlib import Path
import pytest
from pathfinder import budget_reservation as br,budget_group as bg,config,cli
from stubcampaign import make
from test_budget_reservation import approval
from test_served_capacity_extension import add
from test_mixed_capacity_extensions import unserved,pin

def test_first_reservation_then_mixed_extensions_with_shrinking_pending_scope(tmp_path):
 helper=runpy.run_path(str(Path(__file__).resolve().parents[1]/'operator-log/2026-11-03-atlas-pilot16-first-reservation/repin.py'))
 pilot=tmp_path/'pilot';roots=[make(pilot/f'runs/pair-{n}') for n in range(1,7)]
 original=pilot/'original.json';doc=dict(version=1,campaigns=[str(c.root) for c in roots],budget=dict(input_tokens=1000000,output_tokens=100000));br.write_new(original,doc)
 for c in roots:pin(c,original)
 scopes=[(3,4,5,6),(3,4,5,6),(4,5,6),(5,6),(6,),(6,)]
 previous_approval=None
 for i,pairs in enumerate(scopes):
  policy=br.POLICY if i==0 else (br.UNSERVED_EXTENSION if i%2 else br.SERVED_EXTENSION)
  c=roots[pairs[0]-1];call=f'{i+1:032x}';(unserved if policy==br.UNSERVED_EXTENSION else add)(c,call)
  assert bg.report(c)['refusal']
  for n in pairs:
   roots[n-1].path('stop.json').write_text(json.dumps(dict(reason=f'budget: shared group has unknown or invalid input_tokens in {c.root}')))
  p=br.propose(c,call,10000,1000,'OFFLINE explicit estimate',policy=policy);pp=pilot/f'p-{i}.json';br.write_new(pp,p)
  if previous_approval:
   with pytest.raises(ValueError):br.approved_manifest(p,previous_approval)
  a=approval(p);new=br.approved_manifest(p,a)
  assert new['reservations'][:-1]==doc.get('reservations',[]) and new['budget']==doc['budget']
  manifest=pilot/f'm-{i}.json';br.write_new(manifest,new)
  s=helper['snapshot'](pilot,pp,list(pairs));sp=pilot/f's-{i}.json';br.write_new(sp,s)
  journal=c.path(f'transport-evidence/{call}.events.jsonl');assert str(journal) in s['files']
  before={n:r.path('campaign.json').read_bytes() for n,r in enumerate(roots,1)}
  old=journal.read_bytes();journal.write_bytes(old+b'\n')
  with pytest.raises((ValueError,AssertionError)):helper['apply'](manifest,sp)
  assert all(r.path('campaign.json').read_bytes()==before[n] for n,r in enumerate(roots,1))
  journal.write_bytes(old)
  result=helper['apply'](manifest,sp);assert result['repinned']==[str(roots[n-1].root) for n in pairs]
  for n,r in enumerate(roots,1):
   if n not in pairs:assert r.path('campaign.json').read_bytes()==before[n]
   else:
    now=json.loads(r.path('campaign.json').read_text());oldcfg=json.loads(before[n]);now['budget_group']=oldcfg['budget_group'];assert now==oldcfg
    roots[n-1]=config.load(r.root)
    assert bg.report(roots[n-1])['refusal'] is None
    assert cli.main(['--root',str(r.root),'stop','--clear']) in (None,0)
  with pytest.raises(ValueError,match='already reserved'):br.propose(roots[pairs[0]-1],call,10000,1000,'OFFLINE',policy=br.SERVED_EXTENSION if policy==br.POLICY else policy)
  doc=new;previous_approval=a
 assert len(br.records(doc))==6
