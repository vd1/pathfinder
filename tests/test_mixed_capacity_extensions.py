import copy,hashlib,json,runpy
from pathlib import Path
import pytest
from pathfinder import config,budget_group as bg,budget_reservation as br
from test_served_capacity_extension import fixture,add
from test_unserved_capacity import events
from test_budget_reservation import approval
from stubcampaign import make

def unserved(c,call):
 row=add(c,call);lines=[json.dumps(x) for x in events()];data=('\n'.join(lines)+'\n').encode()
 c.path(f'transport-evidence/{call}.events.jsonl').write_bytes(data)
 row.update(raw_events=lines,terminal_event=lines[-1],evidence_journal={'events.jsonl':dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data))})
 rows=c.path('receipts.jsonl').read_text().splitlines();rows[-1]=json.dumps(row);c.path('receipts.jsonl').write_text('\n'.join(rows)+'\n')

def pin(c,path):
 c.raw['budget_group']=dict(manifest=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest());c.path('campaign.json').write_text(json.dumps(c.raw))

def test_repeated_mixed_recurrences_require_independent_approval(tmp_path):
 c,b,old,doc=fixture(tmp_path)
 # Approve the pending served row, then alternate types across different roots.
 previous_approval=None
 for i in range(8):
  policy=br.SERVED_EXTENSION if i%2==0 else br.UNSERVED_EXTENSION
  root=c if i%3 else b
  if i==0:root=c;call='a19a17a5367243c195b33e398b52ecf0'
  else:
   call=f'{i:032x}';(add if policy==br.SERVED_EXTENSION else unserved)(root,call)
  assert bg.report(root)['refusal']
  p=br.propose(root,call,10000,1000,'OFFLINE only',policy=policy)
  if previous_approval:
   with pytest.raises(ValueError):br.approved_manifest(p,previous_approval)
  a=approval(p);new=br.approved_manifest(p,a)
  assert new['reservations'][:-1]==doc['reservations'] and new['budget']==doc['budget']
  assert new['version']==(5 if policy==br.SERVED_EXTENSION else 6)
  path=tmp_path/f'mixed-{i}.json';br.write_new(path,new)
  for x in (c,b):pin(x,path)
  assert bg.report(config.load(root.root))['refusal'] is None
  assert not bg.report(root)['actual_total_certified']
  with pytest.raises(ValueError,match='already reserved'):br.propose(root,call,10000,1000,'OFFLINE',policy=policy)
  bad=copy.deepcopy(new);bad['reservations'][0]['approval']['authority']='altered'
  with pytest.raises(ValueError):br.records(bad)
  doc=new;previous_approval=a
 assert len(br.records(doc))==9

@pytest.mark.parametrize('pairs',[(5,6),(6,)])
def test_pending_only_helper_and_stop_history(tmp_path,pairs):
 helper=runpy.run_path(str(Path(__file__).resolve().parents[1]/'operator-log/2026-11-02-atlas-pilot15-mixed-capacity/repin.py'))
 pilot=tmp_path/'pilot';roots=[make(pilot/f'runs/pair-{n}') for n in range(1,7)]
 old=pilot/'original.json';br.write_new(old,dict(version=1,campaigns=[str(c.root) for c in roots],budget=dict(input_tokens=1000000,output_tokens=100000)))
 for c in roots:pin(c,old)
 first='a'*32;add(roots[3],first)
 p=br.propose(roots[3],first,10000,1000,'OFFLINE baseline',policy=br.POLICY);v2=pilot/'v2.json';br.write_new(v2,br.approved_manifest(p,approval(p)))
 for c in roots:pin(c,v2)
 # Existing served extension means the new failure must extend version 5.
 second='b'*32;add(roots[3],second);p=br.propose(roots[3],second,10000,1000,'OFFLINE',policy=br.SERVED_EXTENSION)
 v5=pilot/'v5.json';br.write_new(v5,br.approved_manifest(p,approval(p)))
 for c in roots:pin(c,v5)
 failing=roots[pairs[0]-1];call='c'*32;unserved(failing,call)
 reason=f'budget: shared group has unknown or invalid input_tokens in {failing.root}'
 for n in pairs:
  roots[n-1].path('stop.json').write_text(json.dumps({'reason':'operator' if n==pairs[0] else reason}))
  roots[n-1].path('events.jsonl').write_text(json.dumps({'kind':'budget-stop','reason':reason})+'\n')
 p=br.propose(failing,call,10000,1000,'OFFLINE',policy=br.UNSERVED_EXTENSION);pp=pilot/'proposal.json';br.write_new(pp,p)
 s=helper['snapshot'](pilot,pp,list(pairs));sp=pilot/'snapshot.json';br.write_new(sp,s)
 assert str(failing.path('events.jsonl')) in s['files']
 v6=pilot/'v6.json';br.write_new(v6,br.approved_manifest(p,approval(p)))
 before={n:c.path('campaign.json').read_bytes() for n,c in enumerate(roots,1)}
 event=failing.path('events.jsonl');saved_event=event.read_bytes();event.write_bytes(saved_event+b'\n')
 with pytest.raises(AssertionError,match='Changed migration binding'):helper['apply'](v6,sp)
 assert all(c.path('campaign.json').read_bytes()==before[n] for n,c in enumerate(roots,1))
 event.write_bytes(saved_event)
 result=helper['apply'](v6,sp);assert result['repinned']==[str(roots[n-1].root) for n in pairs]
 assert set(result['validated_stops_to_clear'])==set(result['repinned'])
 for n,c in enumerate(roots,1):
  now=c.path('campaign.json').read_bytes()
  if n not in pairs:assert now==before[n]
  else:
   a=json.loads(now);b=json.loads(before[n]);a['budget_group']=b['budget_group'];assert a==b
 assert bg.report(config.load(failing.root))['refusal'] is None
