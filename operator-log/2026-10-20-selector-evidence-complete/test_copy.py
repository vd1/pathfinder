import hashlib,importlib.util,json,re
from pathlib import Path
from pathfinder import account_review,pce,pce_recovery
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder')
PACKET=ROOT/'operator-log/2026-10-20-selector-evidence-complete'
spec=importlib.util.spec_from_file_location('copy_helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
PAIR='Q010-P030';IDENTITY='selector-definitions-20261020';REVISION='comparison-scope-1'
sha=lambda x:hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()


def test_same_child_fresh_five_roles_build_and_history(tmp_path,monkeypatch):
    c,dt=helper.copied(tmp_path,monkeypatch,helper.BASE,PAIR,IDENTITY)
    ed=dt/'edited';root=ed/'account-amendments'/IDENTITY/'revisions'/REVISION
    before=pce_recovery.hashes(ed);science=(dt/'status.json').read_bytes();pointer=(ed/'account-amendment.json').read_bytes();candidate=(root/'candidate.tex').read_bytes();request=(root/'request.json').read_bytes()
    old=json.loads((root/'review-grants/clean-context-1/frozen-inputs.json').read_text())
    args=dict(identity=IDENTITY,grant_id='complete-evidence-1',inputs=PACKET/'inputs.json',inputs_sha256=sha((PACKET/'inputs.json').read_bytes()),reason='Copied clean evidence test, no live authority exercised')
    calls=script(monkeypatch,c)
    assert 'no calls' in account_review.apply(c,PAIR,**args)
    target=root/'review-grants/complete-evidence-1'
    frozen=json.loads((target/'frozen-inputs.json').read_text())
    previous=json.loads(old[pce.SUPPLEMENT]);complete=json.loads(frozen[pce.SUPPLEMENT])
    assert all(complete['files'][n]==v for n,v in previous['files'].items())
    original=json.loads((root/'review/frozen-inputs.json').read_text())
    audit=json.loads((PACKET/'external-audit.json').read_text())
    for k,v in original.items():
        if k.startswith('sources/external/amendment-'):assert complete['files'][audit[k]['path']]==v
    assert len(complete['files'])==len(previous['files'])+5
    assert not calls and (ed/'account-amendment.json').read_bytes()==pointer
    assert account_review.workflow(root)==target
    assert 'accepted;' in account_review.apply(c,PAIR,**args,resume=True)
    assert len(calls)==5 and (root/'build/paper.pdf').is_file()
    assert (root/'candidate.tex').read_bytes()==candidate and (root/'request.json').read_bytes()==request
    assert (ed/'account-amendment.json').read_bytes()==pointer
    assert (dt/'status.json').read_bytes()==science
    after=pce_recovery.hashes(ed);assert all(after[n]==h for n,h in before.items() if n!=str((root/'review-active.json').relative_to(ed)))
    for call in calls:
        shown=json.loads(call['prompt'].split('Allowed input files:\n',1)[1])
        if call['role']!='archivist':assert shown[pce.SUPPLEMENT]==frozen[pce.SUPPLEMENT]
        assert not any('prior-review' in name or 'historical-packet' in name for name in shown)
        if call['role'] in ('critic','fact-checker'):
            assert not any(n.startswith(('reviews/','sources/internal/')) for n in shown)
            assert shown[pce.DRAFT].encode()==candidate
    visibility={f.name:json.loads(f.read_text()) for f in (target/'visibility').glob('*.json')}
    assert len(visibility)==5 and all(not v.get('truncated',False) for v in visibility.values())
    assert 'accepted;' in account_review.apply(c,PAIR,**args,resume=True) and len(calls)==5
    (tmp_path/'copy-proof.json').write_text(json.dumps({'prior_files_preserved':len(before),'visibility':visibility,'evidence_manifest':json.loads((target/'evidence-manifest.json').read_text()),'candidate_sha256':sha(candidate)},indent=2))
    print('same child, five fresh stub roles and real build; preserved',len(before),'prior edited files; candidate/request/selected pointer/science exact')
