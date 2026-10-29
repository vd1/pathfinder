import copy,hashlib,json,sys,time
from pathlib import Path
import pytest
from pathfinder import budget_reservation as br,budget_group as bg,provider_evidence as pe,transport,claude_tail
from stubcampaign import make

CALL='6e55ceedf4814fd4948d57d68841a19c'
U=dict(input_tokens=88,output_tokens=78455,cache_creation_input_tokens=151824,cache_read_input_tokens=4730994)
TAIL=dict(input_tokens=2,output_tokens=7,cache_creation_input_tokens=2265,cache_read_input_tokens=158728)
def stream():
 return [dict(type='result',subtype='success',is_error=False,session_id='s',usage=U),
         dict(type='system',subtype='task_notification',session_id='s'),
         dict(type='system',subtype='init',session_id='s'),
         dict(type='assistant',session_id='s',message=dict(usage=TAIL))]
def setup(tmp_path,events=None):
 c=make(tmp_path/'a',budget_usd=1e9)
 group=tmp_path/'group.json';group.write_text(json.dumps(dict(version=1,campaigns=[str(c.root)],budget=dict(input_tokens=1000000000,output_tokens=14000000))))
 c.raw['budget_group']=dict(manifest=str(group),sha256=hashlib.sha256(group.read_bytes()).hexdigest())
 lines=[json.dumps(e) for e in (events or stream())];data=('\n'.join(lines)+'\n').encode()
 c.path('transport-evidence').mkdir();c.path(f'transport-evidence/{CALL}.events.jsonl').write_bytes(data)
 row=dict(call_id=CALL,backend='claude',outcome='completed',usage_completeness='partial',exit_status=-15,
          input_tokens=None,output_tokens=None,usage=TAIL,terminal_event=lines[-1],evidence_journal={'events.jsonl':dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data))})
 c.path('receipts.jsonl').write_text(json.dumps(row)+'\n');return c,row

def propose(c):return br.propose(c,CALL,7382906,103455,'TEST ONLY known first result plus uncertain tail',policy=br.CLAUDE_TAIL_POLICY)
def approval(p):return dict(proposal_sha256=br.digest(p),approved=True,accept_unknown_usage=True,accept_uncertified_actual_total=True,approved_by='OFFLINE',approved_at='test',authority='Synthetic test only')

def test_tail_not_total_even_without_assistant_usage():
 for events in (stream(),stream()[:-1]):
  info=pe.inspect([json.dumps(e) for e in events],completed=True)
  assert info['usage_completeness']=='partial'
 assert pe.inspect([json.dumps(stream()[0])],completed=True)['usage_completeness']=='complete'

def test_canonical_proposal_immutable_and_counts_once(tmp_path):
 c,row=setup(tmp_path);before=c.path('receipts.jsonl').read_bytes()
 p=propose(c);assert p['claude_tail']['completed_totals']==dict(input_tokens=4882906,output_tokens=78455)
 assert bg.report(c)['refusal']
 doc=br.approved_manifest(p,approval(p));path=tmp_path/'approved.json';br.write_new(path,doc)
 c.raw['budget_group']=dict(manifest=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 r=bg.report(c);assert r['refusal'] is None and not r['actual_total_certified']
 assert r['admission_total']==dict(calls=1,input_tokens=7382906,output_tokens=103455)
 assert c.path('receipts.jsonl').read_bytes()==before
 assert transport.receipts(c)[0]['input_tokens'] is None
 # Raw journal binding is revalidated during every admission read.
 c.path(f'transport-evidence/{CALL}.events.jsonl').write_text('tampered')
 with pytest.raises(ValueError,match='journal'):bg.report(c)

@pytest.mark.parametrize('mutation',['error','two-results','no-init','other-session','missing-counter','negative','bool','no-notification'])
def test_other_shapes_refused(tmp_path,mutation):
 events=copy.deepcopy(stream())
 if mutation=='error':events[0]['is_error']=True
 elif mutation=='two-results':events.append(events[0])
 elif mutation=='no-init':events.pop(2)
 elif mutation=='other-session':events[-1]['session_id']='else'
 elif mutation=='missing-counter':del events[0]['usage']['cache_read_input_tokens']
 elif mutation=='negative':events[-1]['message']['usage']['output_tokens']=-1
 elif mutation=='bool':events[0]['usage']['input_tokens']=True
 elif mutation=='no-notification':events.pop(1)
 c,_=setup(tmp_path,events)
 with pytest.raises(ValueError):propose(c)

@pytest.mark.parametrize('mutation',['basis','approval','underreserve','receipt','terminal'])
def test_binding_and_authority_refused(tmp_path,mutation):
 c,row=setup(tmp_path);p=propose(c);a=approval(p)
 if mutation=='basis':p['claude_tail']['completed_totals']['input_tokens']+=1
 elif mutation=='approval':a['accept_unknown_usage']=False
 elif mutation=='underreserve':p['reservation']['output_tokens']=78455
 elif mutation=='receipt':c.path('receipts.jsonl').write_text(json.dumps({**row,'seconds':2})+'\n')
 elif mutation=='terminal':c.path('receipts.jsonl').write_text(json.dumps({**row,'terminal_event':'{}'})+'\n')
 with pytest.raises(ValueError):br.approved_manifest(p,a)


def test_claude_result_does_not_wait_for_background_wakeup(tmp_path,monkeypatch):
 script=tmp_path/'cli.py'
 script.write_text('import json,sys,time\nsys.stdin.read()\nprint(json.dumps(dict(type="system",session_id="s")),flush=True)\n'
   +'print('+repr(json.dumps(stream()[0]))+',flush=True)\ntime.sleep(2)\n'
   +'print('+repr(json.dumps(stream()[-1]))+',flush=True)\ntime.sleep(60)\n')
 c=make(tmp_path/'c',backend='claude',model='m')
 monkeypatch.setenv('PATHFINDER_CLAUDE',f'{sys.executable} {script}')
 t=time.monotonic();r=transport.call('test',campaign=c,model='m',tools=False,search=False,cwd=c.root,timeout=10,thread='Q1P1',stage='peer',actor='ada')
 assert time.monotonic()-t<2
 assert r['ended_after_final_event'] and r['outcome']=='completed'
 assert r['usage']==U and r['usage_completeness']=='complete'
 assert not any(json.loads(line).get('type')=='assistant' for line in r['raw_events'])
