import hashlib,importlib.util,json,re
from pathlib import Path
from pathfinder import account_review,pce,pce_recovery
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder')
PACKET=ROOT/'operator-log/2026-10-20-selector-clean-evidence'
spec=importlib.util.spec_from_file_location('copy_helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
PAIR='Q010-P030';IDENTITY='selector-definitions-20261020';REVISION='comparison-scope-1'
sha=lambda x:hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()


def test_exact_projection_preserves_every_scientific_row_and_file():
    parent=helper.BASE/'threads'/PAIR/'edited/account-amendments'/IDENTITY/'revisions'/REVISION
    f=json.loads((parent/'review/frozen-inputs.json').read_text());supp=f[pce.SUPPLEMENT]
    m=json.loads((PACKET/'projection-manifest.json').read_text());data=json.loads((PACKET/'inputs.json').read_text())['external'];out=json.loads(data['research-supplement.md'])
    assert sha(supp)==m['original_supplement_sha256']
    assert sha((parent/'candidate.tex').read_bytes())==m['candidate_sha256']
    assert data['P.txt']==f['sources/external/P.txt'] and data['Q.txt']==f['sources/external/Q.txt']
    originals={}
    for name,block in re.findall(r'## ([^\n]+)\n(.*?)(?=\n## |\Z)',supp,re.S):
        if not name.endswith('ledger.jsonl'):continue
        for line in block.splitlines():
            match=re.match(r'#(\d+) \[([^,]+), ([^]]+)\] \[([^]]+)\] (.*)',line)
            if match:originals[(name,int(match[1]))]=(match[2],match[3],match[4],match[5])
    visible={}
    for name,text in out['files'].items():
        if name.endswith('ledger.jsonl'):
            for row in map(json.loads,text.splitlines()):visible[(name,row['seq'])]=row
    assert len(originals)==len(visible)==m['ledger_rows']==244
    assert originals.keys()==visible.keys()
    for entry in m['entries']:
        key=(entry['ledger'],entry['seq']);actor,kind,standing,text=originals[key];row=visible[key]
        assert (row['actor'],row['kind'],row['standing'])==(actor,kind,standing)
        assert sha(text)==entry['original_text_sha256']
        reconstructed=''.join(text[a:b] for a,b in entry['kept_spans'])
        assert reconstructed==row['text'] and sha(reconstructed)==entry['projected_text_sha256']
        intervals=sorted(entry['kept_spans']+[[r['start'],r['end']] for r in entry['removed_spans']])
        assert intervals[0][0]==0 and intervals[-1][1]==len(text)
        assert all(a[1]==b[0] for a,b in zip(intervals,intervals[1:]))
        for r in entry['removed_spans']:assert text[r['start']:r['end']]==r['removed']
    files=json.loads(supp.split('## Approved retained scientific files')[1])
    assert len(files)==2
    assert all(out['files'][k]==v for k,v in files.items())
    assert set(out['files'])==set(files)|{k[0] for k in originals}
    clean=json.dumps(out)
    assert not re.search(r'\bverifier\b|\bVera\b|Q2P7\.tex|peer review|review #',clean,re.I)
    # The mixed entry retains the complete physical-comparison limitations/protocol,
    # rather than removing all of entry 64 because it contains an editing sentence.
    old=originals[('ledger.jsonl',64)][3];new=visible[('ledger.jsonl',64)]['text']
    assert new==old.replace('The supplied Q2P7.tex no-finite-shot statement and proposed next selector experiment are superseded; the research call leaves that note unchanged for later editing. ','',1)
    assert 'response-valid larger physical spaces and correlated/basis targets' in new
    assert 'production screening/version/trajectory provenance' in new
    assert 'conservative fitting/forces and representative hydration ensemble uncertainty' in new


def test_same_child_fresh_five_roles_build_and_history(tmp_path,monkeypatch):
    c,dt=helper.copied(tmp_path,monkeypatch,helper.BASE,PAIR,IDENTITY)
    ed=dt/'edited';root=ed/'account-amendments'/IDENTITY/'revisions'/REVISION
    before=pce_recovery.hashes(ed);science=(dt/'status.json').read_bytes();pointer=(ed/'account-amendment.json').read_bytes();candidate=(root/'candidate.tex').read_bytes();request=(root/'request.json').read_bytes()
    old=json.loads((root/'review/frozen-inputs.json').read_text())
    args=dict(identity=IDENTITY,grant_id='clean-context-1',inputs=PACKET/'inputs.json',inputs_sha256=sha((PACKET/'inputs.json').read_bytes()),reason='Copied clean evidence test, no live authority exercised')
    calls=script(monkeypatch,c)
    assert 'no calls' in account_review.apply(c,PAIR,**args)
    target=root/'review-grants/clean-context-1'
    frozen=json.loads((target/'frozen-inputs.json').read_text())
    assert not calls and (ed/'account-amendment.json').read_bytes()==pointer
    assert account_review.workflow(root)==target
    assert 'accepted;' in account_review.apply(c,PAIR,**args,resume=True)
    assert len(calls)==5 and (root/'build/paper.pdf').is_file()
    assert (root/'candidate.tex').read_bytes()==candidate and (root/'request.json').read_bytes()==request
    assert (ed/'account-amendment.json').read_bytes()==pointer
    assert (dt/'status.json').read_bytes()==science
    after=pce_recovery.hashes(ed);assert all(after[n]==h for n,h in before.items())
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
