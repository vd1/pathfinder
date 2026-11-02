import copy,json,hashlib,os
import pytest
from pathfinder import orphan_recovery as o, budget_reservation as br,budget_group as bg,health,config,transport
from test_budget_reservation import setup,proposal,approval,install
CALL='e7e55c64bf35432483adbf8803683cf3'
def fixture(tmp_path,monkeypatch):
 c,b,_=setup(tmp_path);p=proposal(c);old,_=install(tmp_path,c,b,p)
 for x in (c,b):x.path('campaign.json').write_text(json.dumps(x.raw))
 monkeypatch.setattr(o,'boot_time',lambda:2000)
 monkeypatch.setattr(health,'alive',lambda pid: pid==os.getpid())
 d=c.thread_dir('Q1P1');d.mkdir(parents=True)
 (d/'status.json').write_text(json.dumps(dict(stage='peers',status='running',round=5)))
 (d/'ledger.jsonl').write_text(json.dumps(dict(seq=8,actor='verifier',kind='review',text='ITERATE: next'))+'\n')
 (d/'ada').mkdir();(d/'ada/round5.md').write_text('Retained peer work')
 a=dict(attempt_id=CALL,run_id='r',thread='Q1P1',stage='peer',actor='ada',pid=100,child_pid=101,started_at=1900.5,timeout_seconds=600)
 health.write(c.path(f'active-calls/{CALL}.json'),a)
 c.path('transport-evidence').mkdir()
 c.path(f'transport-evidence/{CALL}.events.jsonl').write_text('\n'.join(json.dumps(e) for e in [dict(type='thread.started'),dict(type='turn.started'),dict(type='item.completed',item=dict(type='command_execution'))])+'\n')
 return c,b,old

def test_accounting_recovery_and_idempotent_phase_carry(tmp_path,monkeypatch):
 c,b,old=fixture(tmp_path,monkeypatch);before=c.path('receipts.jsonl').read_bytes();cfg=c.path('campaign.json').read_bytes();work=(c.thread_dir('Q1P1')/'ada/round5.md').read_bytes()
 snap=o.inspect(c,CALL);p=br.propose(c,CALL,10000,1000,'OFFLINE estimate',policy=br.ORPHAN_POLICY)
 assert bg.report(c)['refusal']
 with pytest.raises(ValueError,match='recover-orphan'):health.retire_orphans(c)
 o.recover(c,CALL,apply=True,expected=snap['sha256']);o.recover(c,CALL,apply=True,expected=snap['sha256'])
 assert c.path('receipts.jsonl').read_bytes().startswith(before)
 assert len([r for r in o._rows(c) if r.get('call_id')==CALL])==1
 assert bg.report(c)['refusal'] and br.propose(c,CALL,10000,1000,'OFFLINE estimate',policy=br.ORPHAN_POLICY)==p
 doc=br.approved_manifest(p,approval(p));assert doc['version']==4
 assert doc['reservations'][:-1]==json.loads(old.read_text())['reservations']
 new=tmp_path/'reboot.json';br.write_new(new,doc)
 for x in (c,b):x.raw['budget_group']=dict(manifest=str(new),sha256=hashlib.sha256(new.read_bytes()).hexdigest())
 for x in (c,b):x.path('campaign.json').write_text(json.dumps(x.raw))
 report=bg.report(config.load(b.root));assert report['refusal'] is None and not report['actual_total_certified']
 assert report['reserved']==dict(input_tokens=20000,output_tokens=2000)
 assert {k:v for k,v in json.loads(c.path('campaign.json').read_text()).items() if k!='budget_group'}=={k:v for k,v in json.loads(cfg).items() if k!='budget_group'}
 assert (c.thread_dir('Q1P1')/'ada/round5.md').read_bytes()==work
 assert o.peer_carry(c,'Q1P1',dict(round=5,review_seq=8))==({'ada':100},{'ada':1})
 assert o.peer_carry(c,'Q1P1',dict(round=6,review_seq=9))==({},{})
 with c.path('receipts.jsonl').open('a') as f:f.write(json.dumps(dict(call_id='next',thread='Q1P1',stage='peer',actor='ada',outcome='completed',seconds=12))+'\n')
 assert o.peer_carry(c,'Q1P1',dict(round=5,review_seq=8))==({'ada':112},{'ada':2})

@pytest.mark.parametrize('mutation',['alive','postboot','terminal','missing','stage','receipt','journal-tamper','sha','approval','zero','parent','other-active'])
def test_fail_closed(tmp_path,monkeypatch,mutation):
 c,b,old=fixture(tmp_path,monkeypatch);s=o.inspect(c,CALL);p=br.propose(c,CALL,10000,1000,'OFFLINE',policy=br.ORPHAN_POLICY);ap=approval(p)
 active=c.path(f'active-calls/{CALL}.json');a=json.loads(active.read_text());j=c.path(f'transport-evidence/{CALL}.events.jsonl')
 if mutation=='alive':a['pid']=os.getpid();active.write_text(json.dumps(a))
 elif mutation=='postboot':a['started_at']=2001;active.write_text(json.dumps(a))
 elif mutation=='terminal':j.write_text(j.read_text()+json.dumps(dict(type='turn.completed'))+'\n')
 elif mutation=='missing':j.unlink()
 elif mutation=='stage':a['stage']='verify';active.write_text(json.dumps(a))
 elif mutation=='receipt':
  with c.path('receipts.jsonl').open('a') as f:f.write(json.dumps(dict(call_id=CALL))+'\n')
 elif mutation=='journal-tamper':j.write_text(j.read_text()+'\n')
 elif mutation=='sha':s['sha256']='bad'
 elif mutation=='approval':ap['approved']=False
 elif mutation=='zero':p['reservation']['input_tokens']=0
 elif mutation=='parent':old.write_text(old.read_text()+' ')
 elif mutation=='other-active':health.write(b.path('active-calls/another.json'),{})
 with pytest.raises((ValueError,RuntimeError,OSError)):
  if mutation in ('approval','zero','parent'):br.approved_manifest(p,ap)
  else:o.recover(c,CALL,apply=True,expected=s['sha256'])
 assert not c.path(f'orphan-recoveries/{CALL}.json').exists()
