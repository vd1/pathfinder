import copy,hashlib,json
import pytest
from pathfinder import budget_reservation as br,budget_group as bg,claude_tail,provider_evidence as pe
from test_claude_tail import setup,propose,approval,U

CALL='cce0c93c4a6b43b48ae584ace0bec737'
def fixture(tmp_path):
 c,oldrow=setup(tmp_path)
 p=propose(c);old=br.approved_manifest(p,approval(p));path=tmp_path/'v2.json';br.write_new(path,old)
 c.raw['budget_group']=dict(manifest=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 es=[dict(type='result',subtype='success',is_error=False,session_id='s',usage=U),dict(type='system',subtype='init',session_id='s')]
 lines=[json.dumps(e) for e in es];data=('\n'.join(lines)+'\n').encode()
 c.path(f'transport-evidence/{CALL}.events.jsonl').write_bytes(data)
 row={**oldrow,'call_id':CALL,'exit_status':-9,'usage':U,'terminal_event':lines[-1],
      'evidence_journal':{'events.jsonl':dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data))}}
 with c.path('receipts.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 return c,old,row

def new(c):return br.propose(c,CALL,7382906,103455,'OFFLINE uncertain init-tail estimate',policy=br.CLAUDE_INIT_POLICY)

def test_extension_preserves_prior_approval_and_counts_both(tmp_path):
 c,old,row=fixture(tmp_path);before=c.path('receipts.jsonl').read_bytes()
 p=new(c);basis=p['claude_tail'];assert basis['tail_samples']==[]
 assert basis['completed_usage']==U and basis['observed_tail_message_floor']==dict(input_tokens=0,output_tokens=0)
 manifest=br.approved_manifest(p,approval(p));assert manifest['version']==3
 assert manifest['reservations'][:-1]==old['reservations']
 path=tmp_path/'v3.json';br.write_new(path,manifest)
 c.raw['budget_group']=dict(manifest=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 r=bg.report(c);assert r['refusal'] is None and len(r['unknown_calls'])==2 and not r['actual_total_certified']
 assert r['reserved']==dict(input_tokens=14765812,output_tokens=206910)
 assert c.path('receipts.jsonl').read_bytes()==before
 with pytest.raises(ValueError,match='version 2'):new(c) # no unrestricted chaining

@pytest.mark.parametrize('mutation',['prior','duplicate','scope','approval','zero-tail','basis','journal','receipt'])
def test_tamper_refused(tmp_path,mutation):
 c,old,row=fixture(tmp_path);p=new(c);a=approval(p)
 if mutation=='prior':
  doc=br.approved_manifest(p,a);doc['reservations'][0]['approval']['authority']='changed'
  with pytest.raises(ValueError):br.records(doc)
  return
 if mutation=='duplicate':
  doc=br.approved_manifest(p,a);doc['reservations'].append(doc['reservations'][1])
  with pytest.raises(ValueError):br.records(doc)
  return
 if mutation=='scope':p['scope']['budget']['input_tokens']+=1
 elif mutation=='approval':a['accept_unknown_usage']=False
 elif mutation=='zero-tail':p['reservation']['input_tokens']=4882906
 elif mutation=='basis':p['claude_tail']['tail_samples']=[{}]
 elif mutation=='journal':c.path(f'transport-evidence/{CALL}.events.jsonl').write_text('{}\n')
 elif mutation=='receipt':
  with c.path('receipts.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 with pytest.raises(ValueError):br.approved_manifest(p,a)

@pytest.mark.parametrize('mutation',['assistant','another-init','wrong-session','error-result','usage-init','another-result'])
def test_only_exact_init_suffix_supported(tmp_path,mutation):
 c,old,row=fixture(tmp_path);path=c.path(f'transport-evidence/{CALL}.events.jsonl');es=[json.loads(s) for s in path.read_text().splitlines()]
 if mutation=='assistant':es.append(dict(type='assistant',session_id='s',message={'usage':U}))
 elif mutation=='another-init':es.append(es[-1])
 elif mutation=='wrong-session':es[-1]['session_id']='other'
 elif mutation=='error-result':es[0]['is_error']=True
 elif mutation=='usage-init':es[-1]['usage']=U
 elif mutation=='another-result':es.append(es[0])
 lines=[json.dumps(e) for e in es];data=('\n'.join(lines)+'\n').encode();path.write_bytes(data)
 row['terminal_event']=lines[-1];row['evidence_journal']['events.jsonl']=dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data))
 with pytest.raises(ValueError):claude_tail.evidence(c.root,row,init_only=True)
 assert pe.inspect(lines,completed=True)['usage_completeness']!='complete' or mutation=='another-result'


def test_buffered_init_is_retained_and_not_certified(tmp_path,monkeypatch):
 import sys
 from pathfinder import transport
 from stubcampaign import make
 events=[dict(type='system',session_id='s'),dict(type='result',subtype='success',is_error=False,session_id='s',result='answer',usage=U),dict(type='system',subtype='init',session_id='s')]
 script=tmp_path/'queued.py'
 script.write_text('import sys,time\nsys.stdin.read()\nsys.stdout.write('+repr('\n'.join(json.dumps(e) for e in events)+'\n')+');sys.stdout.flush()\ntime.sleep(60)\n')
 c=make(tmp_path/'c',backend='claude',model='m')
 monkeypatch.setenv('PATHFINDER_CLAUDE',f'{sys.executable} {script}')
 r=transport.call('test',campaign=c,model='m',tools=False,search=False,cwd=c.root,timeout=5,thread='Q1P1',stage='peer',actor='ada')
 assert r['outcome']=='completed' and r['text']=='answer'
 assert r['usage']==U and r['usage_completeness']=='partial'
 assert r['input_tokens'] is None and r['output_tokens'] is None
 assert json.loads(r['terminal_event'])==events[-1]
