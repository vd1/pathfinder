import json,shutil
from pathlib import Path
import pytest
from pathfinder import config,pce,pce_recovery,transport,verify_replay,verifier_receipt,alerts
BASE=Path('/Users/v/Code_2026/nobel/pilot-question/pilot9-control')
PAIR='Q138-P280';CALL='962d2a9323434e7998dbf474ad6da75b'


def setup_copy(tmp_path,monkeypatch):
    monkeypatch.setenv('PATHFINDER_ACCOUNTS',str(tmp_path/'accounts'))
    monkeypatch.setenv('PATHFINDER_OFFLINE','1')
    monkeypatch.setattr(alerts,'_desktop',lambda *a:None)
    monkeypatch.setattr(transport,'execute',lambda *a,**kw:pytest.fail('No model call permitted'))
    original=tmp_path/'original';original.mkdir()
    for n in ['campaign.json','Q.jsonl','P.jsonl','shortlist.json','import.json','receipts.jsonl','run.json','rank-weights.json','acknowledgement.txt']:
        if (BASE/n).exists():shutil.copy(BASE/n,original/n)
    if (BASE/'prompts').exists():shutil.copytree(BASE/'prompts',original/'prompts')
    shutil.copytree(BASE/'threads'/PAIR,original/'threads'/PAIR)
    shutil.copytree(original,tmp_path/'followup')
    return config.load(original),config.load(tmp_path/'followup')

@pytest.mark.parametrize('interrupt',[False,True])
def test_restore_actual_receipt_without_calls(tmp_path,monkeypatch,interrupt):
    original,c=setup_copy(tmp_path,monkeypatch);before=pce_recovery.hashes(original.root)
    d=c.thread_dir(PAIR)
    prepared=verify_replay.run(c,PAIR,origin=original.root,reason='Authorised copied empty-tail restoration',receipt=CALL)
    assert prepared['calls'].startswith('none')
    if interrupt:
        install=verify_replay._install
        monkeypatch.setattr(verify_replay,'_install',lambda *a:(_ for _ in ()).throw(RuntimeError('interrupted')))
        with pytest.raises(RuntimeError,match='interrupted'):verify_replay.run(c,PAIR,apply=True,accept_change='Copied no-call recovery test')
        monkeypatch.setattr(verify_replay,'_install',install)
    result=verify_replay.run(c,PAIR,apply=True,accept_change='Copied no-call recovery test')
    assert result['verdict']['decision']=='ITERATE' and 'score=4/10' in result['verdict']['reason']
    assert result['status']['round']==3 and result['status']['stage']=='peers' and result['status']['status']=='stopped'
    assert pce_recovery.hashes(original.root)==before
    history=json.loads((d/f'{PAIR}.verdict.json').read_text())
    prior=json.loads((original.thread_dir(PAIR)/f'{PAIR}.verdict.json').read_text())
    assert history[:-1]==prior and history[-1]['restored_receipt']==CALL
    assert (d/f'{PAIR}.tex').read_bytes()==(original.thread_dir(PAIR)/f'{PAIR}.tex').read_bytes()
    grant=json.loads((d/'reassessment/request.json').read_text())
    kept=grant['retained_response'];assert kept['original_receipt']['call_id']==CALL
    assert kept['repair_receipt']['call_id']=='8f4753138ddf4ffda251f7fe9d8b940f'
    assert not (d/'reassessment/dispatch.json').exists() and not (d/'reassessment/prompt.txt').exists()
    after=pce_recovery.hashes(d)
    assert verify_replay.run(c,PAIR,apply=True)==result and pce_recovery.hashes(d)==after
    print('Restored exact ITERATE score4 to round3 peers; zero calls; original',len(before),'files preserved; idempotent')

@pytest.mark.parametrize('tamper',['note','history','nonempty_tail','failed_receipt','later_receipt'])
def test_reject_changed_custody(tmp_path,monkeypatch,tamper):
    original,c=setup_copy(tmp_path,monkeypatch);d=original.thread_dir(PAIR)
    if tamper=='note':(d/f'{PAIR}.tex').write_text('changed')
    elif tamper=='history':
        path=d/f'{PAIR}.verdict.json';rows=json.loads(path.read_text());rows[-1]['round']=999;path.write_text(json.dumps(rows))
    else:
        path=original.root/'receipts.jsonl';rows=[json.loads(x) for x in path.read_text().splitlines()]
        r=next(x for x in rows if x.get('call_id')==CALL)
        if tamper=='failed_receipt':r['outcome']='timeout'
        elif tamper=='later_receipt':rows.append({**r,'call_id':'later'})
        else:
            for i,line in enumerate(r['raw_events']):
                e=json.loads(line)
                if e.get('item',{}).get('type')=='agent_message' and not e['item'].get('text'):
                    e['item']['text']='A different answer';r['raw_events'][i]=json.dumps(e)
        path.write_text(''.join(json.dumps(x)+'\n' for x in rows))
    with pytest.raises((pce.Changed,ValueError)):verifier_receipt.inspect(original,PAIR,CALL)

@pytest.mark.parametrize('arm,pair,stage',[
    ('strong','Q462-P471','edit'),('strong','Q138-P280','edit'),
    ('control','Q242-P465','author'),('control','Q177-P500','author'),('control','Q462-P471','author')])
def test_editorial_entry_on_actual_copy(tmp_path,monkeypatch,arm,pair,stage):
    from pathfinder import edit,paper
    base=BASE.parent/('pilot9-'+arm);dst=tmp_path/'copy';dst.mkdir()
    monkeypatch.setenv('PATHFINDER_OFFLINE','1')
    monkeypatch.setenv('PATHFINDER_ACCOUNTS',str(tmp_path/'accounts'))
    for name in ['campaign.json','Q.jsonl','P.jsonl','shortlist.json','rank-weights.json','acknowledgement.txt']:
        if (base/name).exists():shutil.copy(base/name,dst/name)
    if (base/'prompts').exists():shutil.copytree(base/'prompts',dst/'prompts')
    shutil.copytree(base/'threads'/pair,dst/'threads'/pair)
    c=config.load(dst);d=c.thread_dir(pair)
    science=(d/'status.json').read_bytes();note=(d/f'{pair}.tex').read_bytes()
    # Test local compilation and reference consistency without fetching metadata or making calls.
    monkeypatch.setattr(paper,'_arxiv_titles',lambda ids:{})
    class Pending(Exception):pass
    calls=[]
    def capture(prompt,**kw):
        calls.append(kw)
        assert kw['cwd']==d and kw['stage']==stage
        assert 'Workspace contract:' in prompt and str(d.resolve()) in prompt
        assert str(d/('edited/note.tex' if stage=='edit' else 'paper/paper.tex')) in prompt
        raise Pending()
    monkeypatch.setattr(transport,'call',capture)
    monkeypatch.setattr(transport,'execute',lambda *a:pytest.fail('no live transport'))
    if stage=='edit':
        try:result=edit._run(c,pair,lambda:False)
        except Pending:result='pending editor'
        if result=='done':assert not calls
    else:
        with pytest.raises(Pending):paper._run(c,pair,lambda:False)
        result='pending author'
    assert (d/'status.json').read_bytes()==science and (d/f'{pair}.tex').read_bytes()==note
    print(arm,pair,result,'next deadlines',[r['timeout'] for r in calls])
