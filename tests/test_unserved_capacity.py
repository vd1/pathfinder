import copy,hashlib,json
import pytest
from pathlib import Path
from pathfinder import budget_reservation as br,budget_group as bg,transport,cli,unserved_capacity as uc
from test_budget_reservation import setup,approval

CALL='12cb403b779c482db558ee8a5e78ec1c'
WARN='Under-development features enabled: skip_host_skill_discovery. Under-development features are incomplete and may behave unpredictably. To suppress this warning, set `suppress_unstable_features_warning = true` in /Users/test/.codex/config.toml.'

def events():return [dict(type='thread.started',thread_id='thread'),dict(type='item.completed',item=dict(id='item_0',type='error',message=WARN)),dict(type='turn.started'),dict(type='error',message=uc.MESSAGE),dict(type='turn.failed',error=dict(message=uc.MESSAGE))]

def fixture(tmp_path,stream=None):
 c,b,old=setup(tmp_path)
 lines=[json.dumps(e) for e in (stream if stream is not None else events())];data=('\n'.join(lines)+'\n').encode()
 c.path('transport-evidence').mkdir();c.path(f'transport-evidence/{CALL}.events.jsonl').write_bytes(data)
 row=dict(call_id=CALL,backend='codex',outcome='error',error=uc.MESSAGE,failure={'class':'rate'},usage=None,
          input_tokens=None,output_tokens=None,raw_events=lines,terminal_event=lines[-1],evidence_journal={'events.jsonl':dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data))})
 c.path('receipts.jsonl').write_text(json.dumps(row)+'\n')
 return c,b,old,row

def proposal(c,n=100000):return br.propose(c,CALL,n,n//100,'OFFLINE explicit uncertain reservation',policy=br.UNSERVED_POLICY)

@pytest.mark.parametrize('n',[0,100000])
def test_explicit_reservation_keeps_unknown_usage_and_original_receipt(tmp_path,n):
 c,b,old,row=fixture(tmp_path);before=c.path('receipts.jsonl').read_bytes();p=proposal(c,n)
 assert bg.report(c)['refusal'] and p['unserved_evidence']['observed_model_items']==0
 doc=br.approved_manifest(p,approval(p));path=tmp_path/'approved.json';br.write_new(path,doc)
 for a in (c,b):a.raw['budget_group']=dict(manifest=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 r=bg.report(b);assert r['refusal'] is None and not r['actual_total_certified']
 assert r['measured']['calls']==1 and r['reserved']==dict(input_tokens=n,output_tokens=n//100)
 assert r['unknown_calls'][0]['reserved'] and transport.receipts(c)[0]['input_tokens'] is None
 assert c.path('receipts.jsonl').read_bytes()==before
 c.path(f'transport-evidence/{CALL}.events.jsonl').write_text('{}')
 with pytest.raises(ValueError,match='journal'):bg.report(b)

@pytest.mark.parametrize('mutation',['agent_message','reasoning','command_execution','unknown-warning','warning-tools','extra-usage','reordered','two-turns','completed','unknown-event','partial','wrong-error'])
def test_no_model_or_unrecognised_activity_allowed(tmp_path,mutation):
 es=events()
 if mutation in ('agent_message','reasoning','command_execution'):es[1]['item']={'id':'x','type':mutation,'text':'work'}
 elif mutation=='unknown-warning':es[1]['item']['message']='some other error'
 elif mutation=='warning-tools':es[1]['item']['command']='tool'
 elif mutation=='extra-usage':es[-1]['usage']={'input_tokens':1}
 elif mutation=='reordered':es[1],es[2]=es[2],es[1]
 elif mutation=='two-turns':es.insert(3,{'type':'turn.started'})
 elif mutation=='completed':es[-1]={'type':'turn.completed','usage':{}}
 elif mutation=='unknown-event':es.insert(2,{'type':'diagnostic'})
 elif mutation=='partial':es.pop()
 elif mutation=='wrong-error':es[-2]['message']='quota exceeded'
 c,_,_,_=fixture(tmp_path,es)
 with pytest.raises(ValueError):proposal(c)

@pytest.mark.parametrize('mutation',['approval','parent','receipt','classification','cap','negative','bool','fraction','missing-journal','missing-field'])
def test_authority_and_custody(tmp_path,mutation):
 c,b,old,row=fixture(tmp_path);p=proposal(c);a=approval(p)
 if mutation=='approval':a['approved']=False
 elif mutation=='parent':old.write_text(old.read_text()+' ')
 elif mutation=='receipt':c.path('receipts.jsonl').write_text(json.dumps({**row,'seconds':5})+'\n')
 elif mutation=='classification':p['unserved_evidence']['observed_model_items']=1
 elif mutation=='cap':p['scope']['budget']['input_tokens']+=1
 elif mutation in ('negative','bool','fraction'):p['reservation']['input_tokens']={'negative':-1,'bool':True,'fraction':1.5}[mutation]
 elif mutation=='missing-journal':c.path(f'transport-evidence/{CALL}.events.jsonl').unlink()
 elif mutation=='missing-field':del p['unserved_evidence']
 with pytest.raises((ValueError,OSError)):br.approved_manifest(p,a)

def test_cli_policy_and_false_approval(tmp_path):
 c,b,old,row=fixture(tmp_path);c.path('campaign.json').write_text(json.dumps(c.raw));out=tmp_path/'proposal.json'
 assert cli.main(['--root',str(c.root),'budget-reservation','propose','--policy',br.UNSERVED_POLICY,'--call-id',CALL,'--input-tokens','0','--output-tokens','0','--rationale','OFFLINE only','--out',str(out)])==0
 p=json.loads(out.read_text());a=approval(p);a['accept_unknown_usage']=False;ap=tmp_path/'approval.json';ap.write_text(json.dumps(a))
 target=tmp_path/'manifest.json'
 assert cli.main(['budget-reservation','manifest','--proposal',str(out),'--approval',str(ap),'--out',str(target)])==1
 assert not target.exists()

def test_warning_optional_but_served_policy_still_refuses(tmp_path):
 es=events();es.pop(1);c,_,_,_=fixture(tmp_path,es)
 assert proposal(c)['unserved_evidence']['cli_warning_count']==0
 with pytest.raises(ValueError):br.propose(c,CALL,1000,100,'test',policy=br.POLICY)
