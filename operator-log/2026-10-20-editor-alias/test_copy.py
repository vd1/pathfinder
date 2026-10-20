"""Replay exact live receipts on a private copy; dispatch only a stub editor."""
import copy,json,shutil
from pathlib import Path
import pytest
from pathfinder import account_amend,alerts,config,library,paper,pce,pce_recovery,transport
BASE=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2')
ORIGINAL_POOL=library.cache(config.load(BASE)).resolve()
PAIR='Q027-P024'
IDENTITY='rank-norm-20261020'
PACK=Path('/Users/v/Code_2026/pathfinder/operator-log/2026-10-20-rank-norm-locators/Q027-P024')

@pytest.mark.parametrize('limit,interrupted',[(1_000_000,False),(870_000,False),(1_000_000,True)])
def test_pending_editor(tmp_path,monkeypatch,limit,interrupted):
    for key, val in [('PATHFINDER_ACCOUNTS',str(tmp_path/'accounts')),('PATHFINDER_SOURCE_CACHE',str(tmp_path/'pool')),('PATHFINDER_OFFLINE','1')]:
        monkeypatch.setenv(key,val)
    monkeypatch.setattr(alerts,'_desktop',lambda *a:'suppressed')
    monkeypatch.setattr(paper,'_arxiv_titles',lambda ids:{})
    # Keep the path printed in retained prompts exact; no cache accesses or transport calls.
    monkeypatch.setattr(library,'cache',lambda c:ORIGINAL_POOL)
    dst=tmp_path/'copy';dst.mkdir()
    for name in ['campaign.json','import.json','Q.jsonl','P.jsonl','shortlist.json']:
        if (BASE/name).exists():shutil.copy(BASE/name,dst/name)
    st=BASE/'threads'/PAIR;dt=dst/'threads'/PAIR
    shutil.copytree(st,dt)
    c=config.load(dst)
    root=dt/'edited/account-amendments'/IDENTITY
    review=root/'review'
    before=pce_recovery.hashes(dt)
    request=json.loads((root/'request.json').read_text())
    assert not (review/'result.json').exists()
    assert len(list((review/'dispatch').glob('*.json')))==4
    calls=[]
    def dispatch(c,pair,role,prompt,**kw):
        assert role=='editor'
        calls.append(prompt)
        assert len(prompt)<=1_000_000
        packet=json.loads(prompt.split('Allowed input files:\n',1)[1])
        reconstructed={**packet['contents'],**{n:packet['contents'][v] for n,v in packet['aliases'].items()}}
        visibility=json.loads((review/'visibility/pass-01-editor.json').read_text())
        assert visibility['files_sha256']=={n:pce._sha(t) for n,t in reconstructed.items()}
        assert visibility['original_prompt_chars']==1_033_191
        assert visibility['truncated'] is False
        assert len(packet['aliases'])==5
        # Compare every original source, draft, review, and generated history file, not just hashes.
        assert all((review/n).read_bytes().decode('utf-8')==t for n,t in reconstructed.items())
        print('EDITOR',len(prompt),'ORIGINAL',visibility['original_prompt_chars'],'ALIASES',packet['aliases'])
        return {'outcome':'completed','text':json.dumps({'files':{'reviews/editor-feedback.md':json.dumps({'decision':'accept','findings':['Copied pending editor test only.'],'feedback':'All retained gates pass.','evidence_change_requested':False})}})}
    monkeypatch.setattr(pce,'_dispatch',dispatch)
    if limit<1_000_000:
        monkeypatch.setattr(transport,'max_prompt_chars',lambda c:limit)
        cc=copy.copy(c);cc._pce_workflow=review
        with pytest.raises(pce.Changed,match='exceeds prompt allowance'):
            pce.run(cc,PAIR)
        assert not calls
        assert pce_recovery.hashes(dt)==before
        return
    # Existing canonical action, exact authority and original packet, no new grant or budget.
    if interrupted:
        original_write=pce._write
        class Interrupted(Exception):pass
        def write(path,name,text,**kw):
            if name=='result.json':raise Interrupted()
            return original_write(path,name,text,**kw)
        monkeypatch.setattr(pce,'_write',write)
        with pytest.raises(Interrupted):
            account_amend.apply(c,PAIR,identity=IDENTITY,packet=PACK,evidence_root=dt,
                reason=request['reason'],resume=True,accept_change='Private copied pending-editor transport regression')
        assert len(calls)==1 and (review/'dispatch/pass-01-editor.json').exists()
        assert not (review/'result.json').exists()
        monkeypatch.setattr(pce,'_write',original_write)
    result=account_amend.apply(c,PAIR,identity=IDENTITY,packet=PACK,evidence_root=dt,
        reason=request['reason'],resume=True,accept_change='Private copied pending-editor transport regression')
    assert result.startswith('accepted;'),result
    assert len(calls)==1
    after=pce_recovery.hashes(dt)
    assert all(after.get(n)==h for n,h in before.items()),[n for n,h in before.items() if after.get(n)!=h]
    assert (root/'build/paper.pdf').stat().st_size>0
    # Idempotent canonical resume does not dispatch or change accepted artifacts.
    accepted=pce_recovery.hashes(root)
    assert account_amend.apply(c,PAIR,identity=IDENTITY,packet=PACK,evidence_root=dt,
        reason=request['reason'],resume=True).startswith('accepted;')
    assert len(calls)==1 and pce_recovery.hashes(root)==accepted
    print('PRESERVED',len(before),'FILES; FOUR ORIGINAL RECEIPTS; ONE NEW EDITOR; REAL BUILD; IDEMPOTENT RESUME')
