import importlib.util,json,hashlib
from pathlib import Path
from pathfinder import account_revision,account_review,pce,pce_recovery
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder');PACK=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
def test_pending_successor_child(tmp_path,monkeypatch):
    assert Path(account_revision.__file__).resolve().is_relative_to(Path('/private/tmp/pathfinder-clean-c12d7c8'))
    c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q024-P022','allocation-definitions-20261020')
    parent=t/'edited/account-amendments/allocation-definitions-20261020';previous=account_review.workflow(parent)
    assert previous.name=='clean-scientific-inputs-1'
    old=json.loads((previous/'frozen-inputs.json').read_text());assert len(json.loads(old[pce.SUPPLEMENT])['files'])==11
    before=pce_recovery.hashes(t/'edited');science=(t/'status.json').read_bytes();selected=(t/'edited/account-amendment.json').read_bytes();calls=script(monkeypatch,c)
    args=dict(identity='allocation-definitions-20261020',revision='motivation-context-1',packet=PACK/'Q024-P022',reason='Private copied pending successor review')
    assert 'no calls' in account_revision.run(c,'Q024-P022',**args)
    assert (t/'edited/account-amendment.json').read_bytes()==selected
    root=parent/'revisions/motivation-context-1';new=json.loads((root/'review/frozen-inputs.json').read_text())
    assert {k:v for k,v in old.items() if k.startswith('sources/external/')}=={k:v for k,v in new.items() if k.startswith('sources/external/')}
    assert 'accepted;' in account_revision.run(c,'Q024-P022',**args,apply=True);assert len(calls)==5 and (root/'build/paper.pdf').exists()
    assert json.loads((t/'edited/account-amendment.json').read_text())=={'id':args['identity'],'revision':args['revision']}
    after=pce_recovery.hashes(t/'edited');assert all(after[n]==h for n,h in before.items() if n not in ('account-amendment.json','account-successor.json'))
    assert (t/'status.json').read_bytes()==science
    print('5 stub roles + real build;11cleanfiles exact;selected predecessor preserved until acceptance;',len(before),'prior files preserved')

def test_exact_qualifications():
    packet=PACK/'Q024-P022';delta=json.loads((packet/'revision.json').read_text());candidate=(packet/'account-candidate.tex').read_text();original=candidate
    for d in reversed(delta['changes']):assert original.count(d['after'])==1;original=original.replace(d['after'],d['before'])
    assert hashlib.sha256(original.encode()).hexdigest()==delta['parent_candidate_sha256'] and len(delta['changes'])==2
    for phrase in ('do not establish which exact implementation produced the publication runs','archived author manuscript','different encoding','not independently supplied here','without establishing this specific RBFE compiled-cost curve or its novelty'):
        assert phrase in candidate
    context=json.loads((PACK/'retained-context.json').read_text());assert len(context['embedded_sha256'])==11
    assert any(e['seq']==70 and e['kind']=='correction' for e in context['entries']['branches/branch-2/ledger.jsonl'])
