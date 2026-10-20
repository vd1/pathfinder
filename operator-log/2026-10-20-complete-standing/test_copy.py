import importlib.util,json,re,hashlib
from pathlib import Path
from pathfinder import account_revision,pce_recovery
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder')
spec=importlib.util.spec_from_file_location('register_copy',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
PACKET=ROOT/'operator-log/2026-10-20-complete-standing/Q010-P072'

def test_pending_successor_standing_child(tmp_path,monkeypatch):
    base=helper.BASE.parent/'campaign-2-batch-1/Q010-P072';pair='Q010-P072';identity='matrix-control-definition-20261020'
    c,dt=helper.copied(tmp_path,monkeypatch,base,pair,identity)
    before=pce_recovery.hashes(dt/'edited');science=(dt/'status.json').read_bytes();pointer=(dt/'edited/account-amendment.json').read_bytes()
    base_root=dt/'edited/account-amendments'/identity;parent=base_root/'revisions/source-standing-1';candidate=(parent/'candidate.tex').read_text()
    new=(PACKET/'account-candidate.tex').read_text();delta=json.loads((PACKET/'revision.json').read_text())
    assert hashlib.sha256(candidate.encode()).hexdigest()==delta['parent_candidate_sha256']
    transformed=candidate
    for row in delta['changes']:
        assert transformed.count(row['before'])==1
        transformed=transformed.replace(row['before'],row['after'],1)
    assert transformed==new
    assert candidate.split('\\appendix')[1]==new.split('\\appendix')[1]
    assert re.findall(r'\$[^$]*\$|\\begin\{(?:equation\*|align\*)\}.*?\\end\{(?:equation\*|align\*)\}',candidate,re.S)==re.findall(r'\$[^$]*\$|\\begin\{(?:equation\*|align\*)\}.*?\\end\{(?:equation\*|align\*)\}',new,re.S)
    calls=script(monkeypatch,c)
    args=dict(identity=identity,revision='provenance-audit-1',packet=PACKET,reason='Private copied pending successor reader-scope test')
    assert 'no calls' in account_revision.run(c,pair,**args)
    assert (dt/'edited/account-amendment.json').read_bytes()==pointer
    child=base_root/'revisions/provenance-audit-1'
    old=json.loads((parent/'review/frozen-inputs.json').read_text());fresh=json.loads((child/'review/frozen-inputs.json').read_text())
    assert all(fresh[n]==v for n,v in old.items() if n.startswith('sources/external/'))
    assert 'accepted;' in account_revision.run(c,pair,**args,apply=True)
    assert len(calls)==5 and (child/'build/paper.pdf').exists()
    for call in calls:
        if call['role'] in ('fact-checker','critic'):
            shown=json.loads(call['prompt'].split('Allowed input files:\n',1)[1])
            assert shown['sources/external/research-supplement.md']==fresh['sources/external/research-supplement.md']
            assert not any('replacement-history' in name for name in shown)
    register=json.loads((child/'review/replacement-register.json').read_text())
    active=next(x for x in register['claims'] if x['id']=='amendment-16')
    assert "Branch 3's retained finite-kick derivation" in active['text']
    assert "Branch 1's retained measurement-precision audit" in active['text']
    after=pce_recovery.hashes(dt/'edited')
    assert all(after[n]==v for n,v in before.items() if n not in ('account-amendment.json','account-successor.json'))
    assert (dt/'status.json').read_bytes()==science
    assert json.loads((dt/'edited/account-amendment.json').read_text())=={'id':identity,'revision':'provenance-audit-1'}
    print('Five stub roles + real build; preserved',len(before),'prior files except engine pointers; science, equations, matrix definitions, appendix and external projection exact')


def test_registry_math_and_full_provenance_invariants():
    parent=helper.BASE.parent/'campaign-2-batch-1/Q010-P072/threads/Q010-P072/edited/account-amendments/matrix-control-definition-20261020/revisions/source-standing-1'
    old=json.loads((parent/'request.json').read_text())['changes'];new=json.loads((PACKET/'changes.json').read_text());delta=json.loads((PACKET/'revision.json').read_text())
    before=(parent/'candidate.tex').read_text();after=(PACKET/'account-candidate.tex').read_text()
    assert len(old['changes'])==len(new['changes'])==19
    assert old['baseline_sha256']==new['baseline_sha256']
    assert [x['finding'] for x in old['changes']]==[x['finding'] for x in new['changes']]
    assert [x['before'] for x in old['changes']]==[x['before'] for x in new['changes']]
    assert [i+1 for i,(a,b) in enumerate(zip(old['changes'],new['changes'])) if a!=b]==[16]
    assert len(delta['changes'])==2
    restored=after
    for row in reversed(delta['changes']):
        assert restored.count(row['after'])==1;restored=restored.replace(row['after'],row['before'],1)
    assert restored==before
    equations=lambda t:re.findall(r'\$[^$]*\$|\\begin\{(?:equation\*|align\*)\}.*?\\end\{(?:equation\*|align\*)\}',t,re.S)
    assert equations(after)==equations(before)
    numeric=lambda t:re.findall(r'[-+]?\d+(?:\.\d+)?',re.sub(r'Branch [123]', 'Branch',t))
    assert numeric(after)==numeric(before)
    assert after.split('\\appendix')[1]==before.split('\\appendix')[1]
    for phrase in ["Branch 1's inverse-gap omission analysis", "Branch 2's retained regulated-response derivation", "Branch 2's retained response-error derivation", "Branch 3's retained nonlinear-response and representation-error decomposition", "Branch 2's retained molecular-input repository inspection", "Branch 2's retained driving-field versus charge-scaling analysis", "Branch 3's retained finite-kick derivation", "Branch 1's retained measurement-precision audit"]:assert phrase in after
    assert 'not adopted' not in after and 'unadopted' not in after
    context=json.loads((PACKET.parent/'retained-context.json').read_text())
    supplement=json.loads((parent/'review/frozen-inputs.json').read_text())['sources/external/research-supplement.md']
    assert hashlib.sha256(supplement.encode()).hexdigest()==context['frozen_supplement_sha256']
    assert all(q in supplement for q in context['source_quotes'].values())
    assert 'not cited by the joint ledger' in context['source_quotes']['branches/branch-3/ledger.jsonl:8']
    assert 'not cited by the joint ledger' in context['source_quotes']['branches/branch-3/ledger.jsonl:16']
    assert 'not cited by the joint ledger' in context['source_quotes']['branches/branch-1/ledger.jsonl:9']
    files=json.loads(supplement.split('## Approved retained scientific files',1)[1])
    diagnostic=json.loads(files['ada/field-null-diagnostic.json'])
    assert context['joint_circuit_quote'] in diagnostic['resource_boundary']
    assert context['joint_literature']==diagnostic['prior_work']
    assert context['precision_audit_quote'] in files['branches/branch-1/emmy/response-audit.md']
    audit=json.loads((PACKET.parent/'claim-standing-audit.json').read_text())
    assert sorted(i for g in audit['groups'] for i in g['claim_ids'])==[f'C{i:03d}' for i in range(1,99)]
    assert len(audit['mandatory_records'])==11
    standing=json.loads((PACKET.parent/'ledger-standing.json').read_text())
    assert len(standing)==80 and all(x['quote'] in supplement for x in standing.values())
    assert all(hashlib.sha256(x['quote'].encode()).hexdigest()==x['sha256'] for x in standing.values())
    appendix=json.loads((PACKET.parent/'appendix-audit.json').read_text())
    assert appendix['sha256']==hashlib.sha256(after.split('\\appendix',1)[1].encode()).hexdigest()
