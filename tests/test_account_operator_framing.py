import copy,hashlib,json
from types import SimpleNamespace
import pytest
from pathfinder import account_revision as ar,pce
from test_account_revision import prepared
from test_pce import script

def scope(tmp_path):
    (tmp_path/'status.json').write_bytes(b'{"status":"PAUSE"}\n')
    c=SimpleNamespace(thread_dir=lambda pair:tmp_path)
    removed='The thread ended at PAUSE, as specified in the brief. '
    change=dict(finding='operator-framing-status',before=removed+'The model remains unvalidated.',after='The model remains unvalidated.',remove=removed)
    delta=dict(parent_candidate_sha256='parent',changes=[change],operator_framing=dict(kind='operator-framing-v1',authority='Owner authorized exact framing deletion',parent_candidate_sha256='parent',scientific_status_sha256=hashlib.sha256((tmp_path/'status.json').read_bytes()).hexdigest(),changes=[change]))
    return c,delta

def test_separate_operator_scope_only_deletes_exact_status(tmp_path):
    c,d=scope(tmp_path);before=(tmp_path/'status.json').read_bytes()
    assert ar._operator_framing(c,'pair',d)=={'operator-framing-status'}
    assert (tmp_path/'status.json').read_bytes()==before

@pytest.mark.parametrize('damage',['authority','parent','status','science','added','undeclared','empty'])
def test_operator_scope_refuses_wider_or_unbound_edits(tmp_path,damage):
    c,d=scope(tmp_path);s=d['operator_framing'];change=s['changes'][0]
    if damage=='authority':s['authority']=''
    if damage=='parent':s['parent_candidate_sha256']='other'
    if damage=='status':(tmp_path/'status.json').write_text('{"status":"DRAFT"}')
    if damage=='science':change['remove']='The model remains unvalidated.'
    if damage=='added':change['after']='The model is validated.'
    if damage=='undeclared':d['changes']=[]
    if damage=='empty':s['changes']=[]
    with pytest.raises(pce.Changed):ar._operator_framing(c,'pair',d)

@pytest.mark.parametrize('bad',[False,'old-pass','accepted','not-in-history'])
def test_only_terminal_editor_history_can_authorise_revision(tmp_path,monkeypatch,bad):
    c,ed,parent,candidate,args=prepared(tmp_path,monkeypatch)
    review=parent/'review';path=review/'reviews/history/pass-01-editor.json'
    value={'decision':'accept' if bad=='accepted' else 'revise','feedback':'Clarify the empty-set convention.'}
    path.write_text(json.dumps(value));result=json.loads((review/'result.json').read_text())
    result['passes']=2 if bad=='old-pass' else 1
    if bad!='not-in-history':result['history'].append('reviews/history/pass-01-editor.json')
    (review/'result.json').write_text(json.dumps(result))
    packet=args['packet'];d=json.loads((packet/'revision.json').read_text())
    d['findings']=[dict(id='critic-clarity',path='reviews/history/pass-01-editor.json',quote=value['feedback'],sha256=pce._sha(path.read_text()))]
    (packet/'revision.json').write_text(json.dumps(d));calls=script(monkeypatch,c)
    if bad:
        with pytest.raises(pce.Changed):ar.run(c,'Q1P1',**args,apply=True)
        assert not calls
    else:
        assert 'accepted;' in ar.run(c,'Q1P1',**args,apply=True)
        assert len(calls)==5
