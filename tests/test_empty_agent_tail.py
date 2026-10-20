import json
import pytest
from pathfinder import paper,transport

@pytest.mark.parametrize('tail',['','  \n',None])
def test_empty_agent_event_preserves_substantive_reply(tail):
    events=[{'type':'item.completed','item':{'type':'agent_message','text':s}} for s in ['progress','{"decision":"ITERATE"}',tail]]
    events.append({'type':'turn.completed','usage':{'output_tokens':9}})
    result=transport._parse(None,'m',[json.dumps(e) for e in events])
    assert result[0]=='{"decision":"ITERATE"}' and result[2]['output_tokens']==9


def test_last_substantive_reply_still_wins_and_empty_only_stays_empty():
    def parse(values):return transport._parse(None,'m',[json.dumps({'type':'item.completed','item':{'type':'agent_message','text':s}}) for s in values])[0]
    assert parse(['first','last',''])=='last'
    assert parse(['','  '])==''


def test_workspace_contract_anchors_write_and_build_paths(tmp_path):
    import shlex
    root=tmp_path/"thread with 'quotes'"
    for folder,main in [('edited','note.tex'),('paper','paper.tex')]:
        text=paper.workspace_rule(root,folder,main)
        assert str(root/folder/main) in text and str(root/folder/'references.bib') in text
        command=text.split('Compile with this explicit command:\n')[1].split('\n')[0]
        assert shlex.split(command)==['cd',str(root/folder),'&&','latexmk','-pdf','-interaction=nonstopmode','-halt-on-error',main]


def test_empty_verifier_is_not_sent_for_scientific_reformat(tmp_path,monkeypatch):
    from pathfinder import contracts,research
    from stubcampaign import make
    c=make(tmp_path)
    request=research._stage_request(c,'Q1P1','verify','test',True,30)
    monkeypatch.setattr(transport,'execute',lambda *a:pytest.fail('empty reply must not cause a reformat call'))
    value,result=contracts.ensure(c,request,{'text':'  ','transport_failed':False},'verify')
    assert value is None and result['failure']['class']=='contract'
    assert 'no judgment' in result['error']
