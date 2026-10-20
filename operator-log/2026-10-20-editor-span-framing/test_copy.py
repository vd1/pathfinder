import copy,importlib.util,json
from pathlib import Path
import pytest
from pathfinder import account_successor,config,editor_packet,library,pce,pce_recovery,transport
ROOT=Path('/Users/v/Code_2026/pathfinder');BASE=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2');PAIR='Q053-P011';ID='scalar-allowance-definition-20261020';REV=None
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
@pytest.mark.parametrize('mode',['complete','cap','interrupted'])
def test_only_pending_editor(tmp_path,monkeypatch,mode):
    assert Path(pce.__file__).resolve().is_relative_to(Path('/private/tmp/pathfinder-editor-982b7ff'))
    with monkeypatch.context() as local:
        local.delenv('PATHFINDER_SOURCE_CACHE',raising=False)
        pool=library.cache(config.load(BASE)).resolve()
    c,t=helper.copied(tmp_path,monkeypatch,BASE,PAIR,ID,REV);c=config.load(c.root)
    monkeypatch.setattr(library,'cache',lambda c:pool)
    root=t/'edited/account-amendments'/ID;review=root/'review'
    assert not (review/'result.json').exists() and not (review/'dispatch/pass-01-editor.json').exists()
    assert len(list((review/'dispatch').glob('*.json')))==4
    before=pce_recovery.hashes(t);calls=[]
    def dispatch(c,pair,role,prompt,**kw):
        assert role=='editor' and len(prompt)<=1_000_000
        shown=editor_packet.decode_spans(prompt.split('Allowed input files:\n',1)[1])
        visibility=json.loads((review/'visibility/pass-01-editor.json').read_text())
        assert visibility['files_sha256']=={n:pce._sha(v) for n,v in shown.items()}
        assert all((review/n).read_bytes().decode()==v for n,v in shown.items())
        assert len(shown)==20 and len(visibility['file_frames'])==15
        assert visibility['original_prompt_chars']==1232509 and visibility['json_alias_prompt_chars']==1089728
        assert visibility['raw_unique_chars']==1014152 and not visibility['truncated']
        calls.append(prompt)
        return {'outcome':'completed','text':json.dumps({'files':{'reviews/editor-feedback.md':json.dumps({'decision':'accept','findings':['Private pending editor transport test.'],'feedback':'Retained gates pass.','evidence_change_requested':False})}})}
    monkeypatch.setattr(pce,'_dispatch',dispatch)
    args=dict(identity=ID,packet=ROOT/'operator-log/2026-10-20-affinity-scalar-allowance/Q053-P011',reason=json.loads((root/'request.json').read_text())['reason'],apply=True,accept_change='Private copied pending-editor raw framing verification')
    if mode=='cap':
        monkeypatch.setattr(transport,'max_prompt_chars',lambda c:994_000)
        cc=copy.copy(c);cc._pce_workflow=review
        with pytest.raises(pce.Changed,match='exceeds prompt allowance'):pce.run(cc,PAIR)
        assert not calls and pce_recovery.hashes(t)==before
        return
    if mode=='interrupted':
        write=pce._write
        class Interrupted(Exception):pass
        def interrupted(path,name,text,**kw):
            if name=='result.json':raise Interrupted()
            return write(path,name,text,**kw)
        monkeypatch.setattr(pce,'_write',interrupted)
        with pytest.raises(Interrupted):account_successor.run(c,PAIR,**args)
        assert len(calls)==1 and (review/'dispatch/pass-01-editor.json').exists()
        monkeypatch.setattr(pce,'_write',write)
    assert 'accepted;' in account_successor.run(c,PAIR,**args)
    assert len(calls)==1 and (root/'build/paper.pdf').exists()
    after=pce_recovery.hashes(t);assert all(after[n]==h for n,h in before.items() if n not in ('edited/account-amendment.json','edited/account-successor.json'))
    accepted=pce_recovery.hashes(root)
    assert 'accepted;' in account_successor.run(c,PAIR,**args) and len(calls)==1 and pce_recovery.hashes(root)==accepted
    (tmp_path/'proof.json').write_text(json.dumps({'prior_files_preserved':len(before),'visibility':json.loads((review/'visibility/pass-01-editor.json').read_text()),'only_pending_editor':True,'real_build':True,'idempotent':True},indent=2))
    print(mode,'preserved',len(before),'files; editor chars',len(calls[0]))
