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


def _events(c):
    p = c.path('events.jsonl')
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def test_waiting_for_the_group_lock_is_recorded_once_with_its_reason(tmp_path):
    """Atlas pilot 6 (24 October 2026): a reopen runner waited 25 minutes on a busy group with no event."""
    a,b,path=group(tmp_path);fd=open(str(path)+'.lock','w');fcntl.flock(fd,fcntl.LOCK_EX)
    done=threading.Event()
    worker=threading.Thread(target=lambda:(transport.execute(b,request(b)),done.set()),daemon=True);worker.start()
    time.sleep(.5)
    waits=[e for e in _events(b) if e['kind']=='admission_deferred']
    assert len(waits)==1 and 'budget group' in waits[0]['reason'] and 'FIFO' in waits[0]['reason']
    fcntl.flock(fd,fcntl.LOCK_UN);fd.close()
    assert done.wait(5)
    assert len([e for e in _events(b) if e['kind']=='admission_deferred'])==1


def test_a_member_that_just_called_lets_a_waiting_member_go_first(tmp_path,monkeypatch):
    """Back-to-back calls of one controller no longer starve another member polling for the lock."""
    a,b,path=group(tmp_path);doc=json.loads(path.read_text());doc['budget']['calls']=100;path.write_text(json.dumps(doc))
    for c in (a,b):c.raw['budget_group']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    order=[];stop=threading.Event()
    real=transport._execute
    def slow(c,r,*args):
        time.sleep(.2);order.append(c.root.name)
        return real(c,r,*args)
    monkeypatch.setattr(transport,'_execute',slow)
    def chain():                                   # a coordinator: one call after another, no gap of its own
        while not stop.is_set() and order.count('a')<8:transport.execute(a,request(a))
    one=threading.Thread(target=chain,daemon=True);one.start();time.sleep(.3)
    two=threading.Thread(target=lambda:transport.execute(b,request(b)),daemon=True);two.start()
    two.join(5);stop.set();one.join(5)
    assert not two.is_alive() and 'b' in order and order.index('b')<=3


def test_fifo_tickets_skip_dead_owner_and_preserve_registration_order(tmp_path):
    from pathfinder.budget_group import _ticket, _first
    path = tmp_path / 'group.json'
    with _ticket(path) as (q, first):
        with _ticket(path) as (_, second):
            assert _first(q, first)
            assert not _first(q, second)
        # A process that dies releases its flock but may leave the ticket.
        (q / '00000000000000000000.ticket').write_text('stale')
        assert _first(q, first)
        assert not (q / '00000000000000000000.ticket').exists()
    with _ticket(path) as (q, later):
        assert _first(q, later)
    assert not list(q.glob('*.ticket'))


def _queued_process(path, ready, release):
    from pathfinder.budget_group import _ticket
    from pathlib import Path
    with _ticket(Path(path)) as (_, ticket):
        ready.put(ticket.name)
        time.sleep(10)


def test_fifo_liveness_uses_os_lock_across_processes(tmp_path):
    import multiprocessing
    from pathfinder.budget_group import _ticket, _first
    ctx = multiprocessing.get_context('spawn')
    ready, release = ctx.Queue(), ctx.Event()
    path = tmp_path / 'group.json'
    proc = ctx.Process(target=_queued_process, args=(str(path), ready, release))
    proc.start(); name = ready.get(timeout=5)
    try:
        with _ticket(path) as (queue, mine):
            assert mine.name > name and not _first(queue, mine)
            proc.terminate(); proc.join(5)
            assert not proc.is_alive()
            assert _first(queue, mine)
    finally:
        if proc.is_alive(): proc.terminate()
        proc.join(5)
