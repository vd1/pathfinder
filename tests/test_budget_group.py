import hashlib,json,fcntl,threading,time
import pytest
from pathfinder import budget_group,transport,admission
from stubcampaign import make

def group(tmp_path):
    a,b=[make(tmp_path/n) for n in ('a','b')]
    path=tmp_path/'budget-group.json';path.write_text(json.dumps({'version':1,'campaigns':[str(a.root),str(b.root)],'budget':{'calls':2,'input_tokens':100,'output_tokens':20}}))
    for c in (a,b):c.raw['budget_group']={'manifest':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    return a,b,path

def receipt(c,**kw):
    with c.path('receipts.jsonl').open('a') as f:f.write(json.dumps({'outcome':'ok','input_tokens':40,'output_tokens':5,**kw})+'\n')

def request(c):return transport.request('test',model='stub',tools=False,search=False,cwd=c.root,timeout=1,thread='Q1P1',stage='peer',actor='ada')

def test_group_projection_and_dedup(tmp_path):
    a,b,path=group(tmp_path);_,roots,cap=budget_group.load(a)
    assert budget_group.refusal(roots,cap) is None
    receipt(a,call_id='one');receipt(a,call_id='one')
    assert budget_group.refusal(roots,cap) is None
    receipt(b,call_id='two')
    assert 'shared group' in budget_group.refusal(roots,cap)
    with pytest.raises(admission.Refused):transport.execute(b,request(b))
    assert [r['outcome'] for r in transport.receipts(b)]==['ok','refused']

@pytest.mark.parametrize('unknown',['input_tokens','output_tokens','active'])
def test_unknown_spend_fail_closed(tmp_path,unknown):
    a,b,path=group(tmp_path)
    if unknown=='active':
        p=a.path('active-calls');p.mkdir();(p/'unresolved.json').write_text('{}')
    else:receipt(a,**{unknown:None})
    with pytest.raises(admission.Refused):transport.execute(b,request(b))
    assert not b.path('active-calls').exists()

def test_uncharged_and_manifest_tamper(tmp_path):
    a,b,path=group(tmp_path);receipt(a,outcome='launch failed',input_tokens=None,output_tokens=None)
    assert transport.execute(b,request(b))['outcome']=='completed'
    path.write_text('{}')
    with pytest.raises(ValueError,match='hash differs'):transport.execute(b,request(b))

def test_lock_serializes_independent_controllers_and_checks_stop(tmp_path):
    a,b,path=group(tmp_path);fd=open(str(path)+'.lock','w');fcntl.flock(fd,fcntl.LOCK_EX)
    done=threading.Event();errors=[]
    def run():
        try:transport.execute(b,request(b))
        except Exception as e:errors.append(e)
        finally:done.set()
    worker=threading.Thread(target=run,daemon=True);worker.start()
    assert not done.wait(.15)
    b.path('stop.json').write_text('{"reason":"operator stop"}')
    assert done.wait(2);worker.join();fd.close()
    assert len(errors)==1 and isinstance(errors[0],admission.Refused)


def test_receipt_is_committed_before_next_member_admitted(tmp_path,monkeypatch):
    a,b,path=group(tmp_path);doc=json.loads(path.read_text());doc['budget']['calls']=1;path.write_text(json.dumps(doc))
    for c in (a,b):c.raw['budget_group']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    real=transport._execute;entered=threading.Event();release=threading.Event();results=[]
    def slow(c,r,*args):
        entered.set();assert release.wait(3)
        return real(c,r,*args)
    monkeypatch.setattr(transport,'_execute',slow)
    def run(c):
        try:results.append(transport.execute(c,request(c)))
        except admission.Refused as e:results.append(e)
    one=threading.Thread(target=run,args=(a,),daemon=True);two=threading.Thread(target=run,args=(b,),daemon=True)
    one.start();assert entered.wait(2);two.start();time.sleep(.1);release.set()
    one.join(3);two.join(3)
    assert not one.is_alive() and not two.is_alive()
    assert len(results)==2 and sum(isinstance(r,admission.Refused) for r in results)==1
    assert sum(r['outcome'] not in transport.UNCHARGED for c in (a,b) for r in transport.receipts(c))==1
