import json,shutil
from pathlib import Path
import pytest
from pathfinder import account_register as ar,account_revision,account_review,account_release,config,pce,pce_recovery,paper,alerts
from test_pce import script
REPO=Path('/Users/v/Code_2026/pathfinder')
BASE=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2')
ROWS=[('Q010-P030','selector-definitions-20261020','retained-cap-1','2026-10-20-selector-cap'),
 ('Q024-P022','allocation-domain-20261020','training-scope-1','2026-10-20-training-scope'),
 ('Q002-P072','time-swap-definition-20261020','coherence-normalisation-1','2026-10-20-coherence-normalisation'),
 ('Q053-P011','preparation-spec-20261020','feature-scope-1','2026-10-20-feature-scope'),
 ('Q053-P024','conditional-information-20261020','gaussian-noise-1','2026-10-20-gaussian-noise')]

def copied(tmp_path,monkeypatch,base,pair,identity,revision=None):
    for key,val in [('PATHFINDER_ACCOUNTS',str(tmp_path/'accounts')),('PATHFINDER_SOURCE_CACHE',str(tmp_path/'pool')),('PATHFINDER_OFFLINE','1')]:monkeypatch.setenv(key,val)
    monkeypatch.setattr(alerts,'_desktop',lambda *a:None);monkeypatch.setattr(paper,'_arxiv_titles',lambda ids:{})
    dst=tmp_path/'copy';dst.mkdir()
    for name in ['campaign.json','import.json','Q.jsonl','P.jsonl','shortlist.json']:
        if (base/name).exists():shutil.copy(base/name,dst/name)
    st=base/'threads'/pair;dt=dst/'threads'/pair;dt.mkdir(parents=True)
    for p in st.iterdir():
        if p.is_file() and p.suffix in ('.json','.jsonl','.tex'):shutil.copy(p,dt/p.name)
    for name in ('edited','inputs'):shutil.copytree(st/name,dt/name)
    for p in st.glob('branches/*/ledger.jsonl'):
        dest=dt/p.relative_to(st);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest)
    root=st/'edited/account-amendments'/identity
    if revision:root=root/'revisions'/revision
    for name in json.loads((root/'evidence-snapshots.json').read_text()):
        dest=dt/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(st/name,dest)
    c=config.load(dst);c.backend='stub';c.raw['routes']={};c.raw['refusal_fallback']=None
    return c,dt

@pytest.mark.parametrize('pair,identity,revision,packet',ROWS)
def test_ready_child(tmp_path,monkeypatch,pair,identity,revision,packet):
    c,dt=copied(tmp_path,monkeypatch,BASE,pair,identity)
    existing=dt/'edited/account-amendments'/identity/'revisions'/revision
    if existing.exists():
        # Operator may have launched a legacy grant since the earlier copied five-role proof.
        # Validate its packet without resetting or rerunning that live-derived snapshot.
        history=json.loads((REPO/'operator-log'/packet/pair/'changes.json').read_text())
        parent=dt/'edited/account-amendments'/identity
        original,_,_=account_release.source(c,pair)
        register=ar.build(original,history['changes'],(REPO/'operator-log'/packet/pair/'account-candidate.tex').read_text())
        assert all(r['status']=='surviving' for r in register['records'])
        return
    before=pce_recovery.hashes(dt/'edited');science=(dt/'status.json').read_bytes()
    calls=script(monkeypatch,c)
    args=dict(identity=identity,revision=revision,packet=REPO/'operator-log'/packet/pair,reason='Private copied final-register validation')
    assert 'no calls' in account_revision.run(c,pair,**args)
    root=dt/'edited/account-amendments'/identity/'revisions'/revision;review=root/'review'
    register=json.loads((review/'replacement-register.json').read_text())
    assert all(all((root/'candidate.tex').read_text()[a:b] in claim['claim'] for a,b in claim['final_spans']) for claim in register['records'])
    parent=dt/'edited/account-amendments'/identity
    # The active parent can itself be a prior child; the register still binds original-baseline custody.
    frozen=json.loads((review/'frozen-inputs.json').read_text())
    assert 'accepted;' in account_revision.run(c,pair,**args,apply=True)
    assert len(calls)==5
    for call in calls:
        if call['role'] in ('fact-checker','critic'):
            shown=json.loads(call['prompt'].split('Allowed input files:\n',1)[1])
            assert shown[pce.SUPPLEMENT]==frozen[pce.SUPPLEMENT]
            assert not any('replacement-history' in n for n in shown)
    after=pce_recovery.hashes(dt/'edited')
    assert all(after[n]==h for n,h in before.items() if n!='account-amendment.json')
    assert (dt/'status.json').read_bytes()==science
    assert (root/'build/paper.pdf').exists()
    print(pair,'5 stub roles, real build; statuses',[x['status'] for x in register['records']], 'preserved',len(before))


def test_same_child_register_repair(tmp_path,monkeypatch):
    base=BASE.parent/'campaign-2-batch-1/Q010-P072';pair='Q010-P072';identity='shot-budget-withdrawal-20261020';revision='definitions-1'
    c,dt=copied(tmp_path,monkeypatch,base,pair,identity,revision)
    root=dt/'edited/account-amendments'/identity/'revisions'/revision
    before=pce_recovery.hashes(dt/'edited');science=(dt/'status.json').read_bytes();calls=script(monkeypatch,c)
    args=dict(identity=identity,revision=revision,reason='Private copied superseded register repair')
    assert 'no calls' in ar.repair(c,pair,**args)
    target=account_review.workflow(root);old=json.loads((root/'review/frozen-inputs.json').read_text());new=json.loads((target/'frozen-inputs.json').read_text())
    assert all(new[n]==t for n,t in old.items() if n!='sources/internal/changes.json')
    r=json.loads((target/'replacement-register.json').read_text())
    assert r['records'][3]['status']=='superseded'
    assert not any(x['id']=='amendment-4' for x in r['claims'])
    assert 'accepted;' in ar.repair(c,pair,**args,apply=True)
    assert len(calls)==5
    after=pce_recovery.hashes(dt/'edited');assert all(after[n]==h for n,h in before.items() if n!='account-amendment.json')
    assert (dt/'status.json').read_bytes()==science
    assert (root/'build/paper.pdf').exists()
    assert ar.repair(c,pair,**args,apply=True).startswith('accepted;') and len(calls)==5
    account_release.view(c,pair,create=True)
    print(pair,'same child, 5 stub roles, real build; obsolete amendment-4 suppressed; prior files',len(before))
