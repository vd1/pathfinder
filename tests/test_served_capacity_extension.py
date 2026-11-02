import copy,hashlib,json,time
from contextlib import contextmanager
import pytest
from pathlib import Path
from pathfinder import budget_reservation as br,budget_group as bg,served_capacity as sc,transport,provider_cooldown,config
from test_budget_reservation import setup,proposal,approval,install
CALL='a19a17a5367243c195b33e398b52ecf0'
def add(c,call=CALL):
 es=[dict(type='thread.started',thread_id='thread'),dict(type='turn.started'),dict(type='item.completed',item=dict(id='i',type='command_execution',command='read file')),dict(type='error',message=sc.MESSAGE),dict(type='turn.failed',error=dict(message=sc.MESSAGE))]
 lines=[json.dumps(x) for x in es];data=('\n'.join(lines)+'\n').encode();c.path('transport-evidence').mkdir(exist_ok=True)
 c.path(f'transport-evidence/{call}.events.jsonl').write_bytes(data)
 row=dict(call_id=call,backend='codex',outcome='error',stage='consolidate',error=sc.MESSAGE,failure={'class':'rate'},usage=None,input_tokens=None,output_tokens=None,cache_read=None,cache_write=None,raw_events=lines,terminal_event=lines[-1],evidence_journal={'events.jsonl':dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data))})
 with c.path('receipts.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 return row

def fixture(tmp_path):
 c,b,_=setup(tmp_path);p=proposal(c);old,doc=install(tmp_path,c,b,p);add(c)
 return c,b,old,doc

def extend(c,call=CALL):return br.propose(c,call,10000,1000,'TEST historical estimate, not measured',policy=br.SERVED_EXTENSION)

def test_recurrence_needs_fresh_approval_and_preserves_chain(tmp_path):
 c,b,old,doc=fixture(tmp_path);before=c.path('receipts.jsonl').read_bytes()
 for i in range(5):
  call=CALL if i==0 else f'{i:032x}'
  if i:add(c,call)
  assert bg.report(c)['refusal']
  p=extend(c,call);a=approval(p)
  if i:
   with pytest.raises(ValueError):br.approved_manifest(p,previous_approval)
  new=br.approved_manifest(p,a);assert new['reservations'][:-1]==doc['reservations']
  f=tmp_path/f'extension-{i}.json';br.write_new(f,new)
  for x in (c,b):x.raw['budget_group']=dict(manifest=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest())
  assert bg.report(b)['refusal'] is None and not bg.report(b)['actual_total_certified']
  with pytest.raises(ValueError,match='already reserved'):extend(c,call)
  doc=new;previous_approval=a
 assert c.path('receipts.jsonl').read_bytes().startswith(before)
 assert len(br.records(doc))==6

@pytest.mark.parametrize('change',['approval','amount','parent','prior','journal','raw','terminal','no-service','usage','class','completed','zero'])
def test_custody_and_scope(tmp_path,change):
 c,b,old,doc=fixture(tmp_path);p=extend(c);a=approval(p)
 if change=='approval':a['approved']=False
 elif change=='amount':p['reservation']['input_tokens']+=1
 elif change=='parent':old.write_text(old.read_text()+' ')
 elif change=='prior':
  n=br.approved_manifest(p,a);n['reservations'][0]['approval']['authority']='changed'
  with pytest.raises(ValueError):br.records(n)
  return
 elif change=='journal':c.path(f'transport-evidence/{CALL}.events.jsonl').write_text('{}')
 elif change=='zero':p['reservation']['input_tokens']=0
 else:
  rows=[json.loads(x) for x in c.path('receipts.jsonl').read_text().splitlines()];r=rows[-1]
  if change=='raw':r['raw_events'].pop(2)
  elif change=='terminal':r['terminal_event']='{}'
  elif change=='no-service':
   r['raw_events'].pop(2);data=('\n'.join(r['raw_events'])+'\n').encode();c.path(f'transport-evidence/{CALL}.events.jsonl').write_bytes(data);r['evidence_journal']['events.jsonl']=dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data))
  elif change=='usage':r['usage']={'input_tokens':1}
  elif change=='class':r['failure']['class']='quota'
  elif change=='completed':r['outcome']='completed'
  c.path('receipts.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
 with pytest.raises(ValueError):br.approved_manifest(p,a)

def test_retry_reaches_budget_after_provider_gate_but_never_dispatches(tmp_path,monkeypatch):
 c,b,_,_=fixture(tmp_path);order=[]
 @contextmanager
 def gate(*args):order.append('provider passed');yield {}
 monkeypatch.setattr(provider_cooldown,'gate',gate)
 monkeypatch.setattr(transport,'_attempt',lambda *a:pytest.fail('must not dispatch'))
 request=transport.ModelRequest(identity='x',prompt='test',model='stub',tools=False,search=False,cwd=c.root,timeout=60,thread='Q1P1',stage='consolidate',actor='ada')
 with pytest.raises(Exception,match='unknown or invalid input_tokens'):transport._admitted_attempt(c,request,time.monotonic()+60)
 assert order==['provider passed']
 assert 'unknown or invalid input_tokens' in json.loads(c.path('stop.json').read_text())['reason']
 assert not list(c.path('active-calls').glob('*.json'))


def test_canonical_compacted_receipt_keeps_full_journal_binding(tmp_path):
 from pathfinder import gc
 c,b,old,doc=fixture(tmp_path)
 rows=[json.loads(x) for x in c.path('receipts.jsonl').read_text().splitlines()];r=rows[-1]
 events=[json.loads(x) for x in r['raw_events']];events[2]['item']['aggregated_output']='long output '*1000
 lines=[json.dumps(x) for x in events];data=('\n'.join(lines)+'\n').encode()
 c.path(f'transport-evidence/{CALL}.events.jsonl').write_bytes(data)
 r['raw_events']=gc.compact_events(lines);r['evidence_journal']['events.jsonl']=dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data))
 c.path('receipts.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
 assert extend(c)['served_evidence']['journal_size']==len(data)
