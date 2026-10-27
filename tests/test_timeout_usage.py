import hashlib,json,sys
from pathlib import Path
import pytest
from pathfinder import provider_evidence as pe,usage_recovery as recovery,transport,failures,budget_group
from stubcampaign import make

USAGE=dict(input_tokens=2,output_tokens=298,cache_creation_input_tokens=101209,cache_read_input_tokens=5024)

def event(**kw):
    return json.dumps(dict(type='result',is_error=True,result='Request timed out',usage=USAGE,**kw))


def fixture(tmp_path):
    c=make(tmp_path)
    line=event();data=(line+'\n').encode()
    c.path('transport-evidence').mkdir()
    c.path('transport-evidence/failed.events.jsonl').write_bytes(data)
    row=dict(call_id='failed',backend='claude',outcome='error',error='Request timed out',input_tokens=None,
             output_tokens=None,cache_read=None,cache_write=None,usage=USAGE,terminal_event=line,
             usage_completeness='partial',evidence_journal={'events.jsonl':{
                 'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)}})
    c.path('receipts.jsonl').write_text(json.dumps(row)+'\n')
    return c,row


def test_failed_final_totals_are_complete_but_partial_streams_are_not():
    assert pe.inspect([event()])['usage_completeness']=='complete'
    assert failures.classify('error','Request timed out').record()['class']=='timeout'
    assert failures.classify('completed',None) is None
    assert pe.inspect([json.dumps(dict(type='assistant',message={'usage':USAGE}))])['usage_completeness']=='partial'
    assert pe.terminal_result_usage([event(),'{incomplete']) is None
    for key in USAGE:
        for invalid in (None,True,-1,'2'):
            usage={**USAGE,key:invalid}
            assert pe.terminal_result_usage([json.dumps(dict(type='result',is_error=True,usage=usage))]) is None


def test_immutable_correction_restores_whole_input_accounting(tmp_path):
    c,row=fixture(tmp_path);before=c.path('receipts.jsonl').read_bytes()
    assert budget_group.refusal([c.root],{'input_tokens':1000000})
    plan=recovery.recover(c,'failed','restore reported final totals')
    assert not c.path('usage-corrections/failed.json').exists()
    recovery.recover(c,'failed','restore reported final totals',apply=True,expected=plan['sha256'])
    r=transport.receipts(c)[0]
    assert (r['input_tokens'],r['output_tokens'],r['input_tokens_uncached'])==(106235,298,2)
    assert r['outcome']=='error' and r['error']=='Request timed out'
    assert budget_group.refusal([c.root],{'input_tokens':1000000}) is None
    assert c.path('receipts.jsonl').read_bytes()==before
    with pytest.raises(ValueError,match='already'): recovery.recover(c,'failed','again')


@pytest.mark.parametrize('mutation',['journal','receipt','proposal','active'])
def test_invalid_recovery_is_refused_without_mutation(tmp_path,mutation):
    c,row=fixture(tmp_path);plan=recovery.recover(c,'failed','fix')
    expected=plan['sha256']
    if mutation=='journal':c.path('transport-evidence/failed.events.jsonl').write_text(event()+'extra')
    elif mutation=='receipt':
        row['usage']={**USAGE,'input_tokens':99};c.path('receipts.jsonl').write_text(json.dumps(row)+'\n')
    elif mutation=='proposal':expected='wrong'
    else:
        c.path('active-calls').mkdir();c.path('active-calls/unknown.json').write_text('{}')
    with pytest.raises((ValueError,RuntimeError)):recovery.recover(c,'failed','fix',apply=True,expected=expected)
    assert not c.path('usage-corrections/failed.json').exists()


def test_overlay_tampering_fails_closed(tmp_path):
    c,row=fixture(tmp_path);plan=recovery.recover(c,'failed','fix')
    recovery.recover(c,'failed','fix',apply=True,expected=plan['sha256'])
    p=c.path('usage-corrections/failed.json');doc=json.loads(p.read_text());doc['fields']['input_tokens']=0
    doc['sha256']=recovery.digest({k:v for k,v in doc.items() if k!='sha256'});p.write_text(json.dumps(doc))
    with pytest.raises(ValueError):transport.receipts(c)


def test_real_fake_cli_timeout_retries_once_and_keeps_known_usage(tmp_path,monkeypatch):
    fake=f'{sys.executable} {Path(__file__).parent / "fake_cli.py"}'
    c=make(tmp_path,backend='claude',model='m',transient_backoff_seconds=[0],retry_jitter_fraction=0)
    monkeypatch.setenv('PATHFINDER_CLAUDE',fake)
    monkeypatch.setenv('FAKE_ERROR','1');monkeypatch.setenv('FAKE_REPLY','Request timed out')
    monkeypatch.setenv('FAKE_USAGE',json.dumps(USAGE))
    r=transport.call('p',campaign=c,model='m',tools=False,search=False,cwd=tmp_path,timeout=10,
                     thread='Q1P1',stage='consolidate',actor='ada')
    assert r['transport_failed'] and r['failure']['class']=='timeout'
    rows=transport.receipts(c)
    assert len(rows)==2 and all(x['input_tokens']==106235 and x['output_tokens']==298 for x in rows)
    assert all(x['outcome']=='error' for x in rows)


def test_shared_group_lock_blocks_accounting_change(tmp_path):
    import fcntl
    c,row=fixture(tmp_path/'c');group=tmp_path/'group.json'
    group.write_text(json.dumps({'version':1,'campaigns':[str(c.root)],'budget':{'input_tokens':1000000}}))
    c.raw['budget_group']={'manifest':str(group),'sha256':hashlib.sha256(group.read_bytes()).hexdigest()}
    with open(str(group)+'.lock','a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        with pytest.raises(ValueError,match='group call is active'):recovery.recover(c,'failed','fix')
    assert not c.path('usage-corrections/failed.json').exists()


def test_legacy_receipt_identity_has_no_new_path_interpretation(tmp_path):
    c=make(tmp_path)
    row={'call_id':'legacy:one','outcome':'completed','input_tokens':1,'output_tokens':2}
    c.path('receipts.jsonl').write_text(json.dumps(row)+'\n')
    assert transport.receipts(c)==[row]
