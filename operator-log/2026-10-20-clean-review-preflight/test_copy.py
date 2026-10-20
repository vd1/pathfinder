import hashlib,importlib.util,json,shutil
from pathlib import Path
import pytest
from pathfinder import account_review,account_revision,account_successor,pce,pce_recovery
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder');PACK=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
CASES={'affinity':('Q053-P011','preparation-spec-20261020','affinity-cycle-definitions-1'),'bundle':('Q053-P024','conditional-information-20261020','gaussian-noise-framing-1'),'allocation':('Q024-P022','allocation-domain-20261020','aggregate-validation-1')}
sha=lambda b:hashlib.sha256(b).hexdigest()
@pytest.mark.parametrize('tag',CASES)
def test_clean_copy(tmp_path,monkeypatch,tag):
    pair,identity,revision=CASES[tag]
    c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,pair,identity,revision)
    before=pce_recovery.hashes(t/'edited');science=(t/'status.json').read_bytes()
    calls=script(monkeypatch,c)
    if tag=='bundle':
        revision='bundle-definition-1'
        account_revision.run(c,pair,identity=identity,revision=revision,packet=ROOT/'operator-log/2026-10-20-bundle-definitions/Q053-P024',reason='Private copied preparation')
    if tag=='allocation':
        packet=ROOT/'operator-log/2026-10-20-allocation-definitions/Q024-P022'
        delta=json.loads((packet/'successor.json').read_text())
        for row in delta['evidence_projection']['include']:
            dst=t/row['path'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(helper.BASE/'threads'/pair/row['path'],dst)
        identity='allocation-definitions-20261020';revision=None
        account_successor.run(c,pair,identity=identity,packet=packet,reason='Private copied preparation')
    root=t/'edited/account-amendments'/identity
    if revision:root=root/'revisions'/revision
    candidate=(root/'candidate.tex').read_bytes();request=(root/'request.json').read_bytes()
    args=dict(identity=identity,grant_id='clean-scientific-inputs-1',inputs=PACK/tag/'inputs.json',inputs_sha256=sha((PACK/tag/'inputs.json').read_bytes()),reason='Private copied clean scientific transport test',before_first_call=tag!='affinity')
    assert 'no calls' in account_review.apply(c,pair,**args) and not calls
    assert 'accepted;' in account_review.apply(c,pair,**args,resume=True)
    assert len(calls)==5 and (root/'build/paper.pdf').exists()
    assert (root/'candidate.tex').read_bytes()==candidate and (root/'request.json').read_bytes()==request
    assert (t/'status.json').read_bytes()==science
    after=pce_recovery.hashes(t/'edited')
    mutable={'account-amendment.json','account-successor.json',str((root/'review-active.json').relative_to(t/'edited'))}
    assert all(after[n]==h for n,h in before.items() if n not in mutable)
    target=account_review.workflow(root);frozen=json.loads((target/'frozen-inputs.json').read_text())
    expected=json.loads((PACK/tag/'inputs.json').read_text())['external']
    assert all(frozen['sources/external/'+k]==v for k,v in expected.items() if k!='research-supplement.md')
    assert json.loads(frozen[pce.SUPPLEMENT])==json.loads(expected['research-supplement.md'])
    for call in calls:
        if call['role']=='archivist':continue
        shown=json.loads(call['prompt'].split('Allowed input files:\n',1)[1]);assert shown[pce.SUPPLEMENT]==frozen[pce.SUPPLEMENT]
    visibility=[json.loads(f.read_text()) for f in (target/'visibility').glob('*.json')]
    assert len(visibility)==5 and all(not v.get('truncated',False) for v in visibility)
    print(tag,'five roles, real build, preserved',len(before),'files; prompt chars',[len(x['prompt']) for x in calls])

@pytest.mark.parametrize('tag',CASES)
def test_projection_coverage(tag):
    import re
    pair,identity,revision=CASES[tag]
    root=helper.BASE/'threads'/pair/'edited/account-amendments'/identity/'revisions'/revision
    original=json.loads((root/'review/frozen-inputs.json').read_text())
    supplement=original[pce.SUPPLEMENT];snap=json.loads((root/'evidence-snapshots.json').read_text())
    audit=json.loads((PACK/tag/'projection-manifest.json').read_text())
    projected=json.loads(json.loads((PACK/tag/'inputs.json').read_text())['external']['research-supplement.md'])['files']
    assert set(audit['external_inventory'])=={k for k in original if k.startswith('sources/external/')}
    ledger={}
    for m in re.finditer(r'## ([^\n]+)\n(.*?)(?=\n## |\Z)',supplement,re.S):
        if not m[1].endswith('ledger.jsonl'):continue
        rows=[]
        for line in m[2].splitlines():
            r=re.fullmatch(r'#(\d+) \[([^,]+), ([^]]+)\] \[([^]]+)\] (.*)',line)
            if r:rows.append(dict(seq=int(r[1]),actor=r[2],kind=r[3],standing=r[4],text=r[5]))
        ledger[m[1]]=rows
    embedded=json.loads(supplement.split('## Approved retained scientific files',1)[1])
    def check(text,new,a):
        assert sha(text.encode())==a['original_sha256'] and sha(new.encode())==a['projected_sha256']
        spans=[(x,y) for x,y in a['kept_spans']]+[(x['start'],x['end']) for x in a['removed_spans']]
        pos=0
        for start,end in sorted(spans):assert start==pos and end>start;pos=end
        assert pos==len(text)
        assert new==''.join(text[x:y] for x,y in a['kept_spans'])
        for row in a['removed_spans']:assert text[row['start']:row['end']]==row['text']
    for name,a in audit['files'].items():
        if a['kind']=='ledger':
            rows=[json.loads(x) for x in projected[name].splitlines()]
            assert len(rows)==len(ledger[name])==len(a['entries'])
            for old,new,entry in zip(ledger[name],rows,a['entries']):
                assert {k:v for k,v in old.items() if k!='text'}=={k:v for k,v in new.items() if k!='text'}
                check(old['text'],new['text'],entry)
                if tag=='bundle' and not old['text'].startswith(('Ada current account','Current account')):
                    assert len(re.findall(r'(?<![-\w])R1 ',old['text']))==len(re.findall(r'(?<![-\w])R1 ',new['text']))
        else:
            if name in embedded:text=embedded[name]
            elif name in snap:text=snap[name]
            else:
                keys=[k for k,v in audit['external_inventory'].items() if v.get('path')==name]
                text=original[keys[0]] if keys else (helper.BASE/'threads'/pair/name).read_bytes().decode()
            check(text,projected[name],a)
    assert len(ledger)==sum(a['kind']=='ledger' for a in audit['files'].values())
    assert set(embedded)<=set(projected)
