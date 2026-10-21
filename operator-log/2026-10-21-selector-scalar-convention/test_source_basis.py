"""Complete retained implementation citations through all role scopes, using offline stub replies."""
import importlib.util
import json
from pathlib import Path
import pytest
from pathfinder import account_revision, pce, stub
from test_pce import script

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('copy_proof',HERE/'test_copy.py')
proof=importlib.util.module_from_spec(spec);spec.loader.exec_module(proof)


@pytest.mark.parametrize('basis',['research record','papers'])
def test_actual_selected_record_citation(tmp_path,monkeypatch,basis):
    c,t,args=proof.setup(tmp_path,monkeypatch)
    source='sources/external/amendment-retained-'+pce._sha('ada/adapt_qsci/build.py')[:16]+'.txt'
    claim='The stored parent matrices exclude the inactive-plus-nuclear scalar, with core and delta_core stored separately.'
    def author(prompt):
        shown=json.loads(prompt.split('Allowed input files:\n',1)[1])
        assert source in shown
        assert 'Classify support from them as research record' in shown['brief.md']
        assert 'parent.append(projected)' in shown[source]
        assert 'core=core,delta_core=core1-core' in shown[source]
        return json.dumps({'files':{'claims/current.json':json.dumps([
            {'id':'scalar-storage','text':claim,'kind':'fact','location':'Frequency pooling',
             'status':'needs-review'}])}})
    def fact(prompt):
        shown=json.loads(prompt.split('Allowed input files:\n',1)[1])
        assert source in shown
        assert 'Classify support from them as research record' in shown['brief.md']
        assert not any(n.startswith(('sources/internal/','reviews/','revisions/')) for n in shown)
        out=json.loads(stub.pce_reply(c,'fact-checker',prompt))
        for name,text in out['files'].items():
            report=json.loads(text)
            selected=next(r for r in report['claims'] if r['id']=='scalar-storage')
            selected['basis']=basis
            selected['evidence']=[source+'#exact-probability-ranking']
            out['files'][name]=json.dumps(report)
        return json.dumps(out)
    calls=script(monkeypatch,c,author=[author],fact_checker=[fact])
    result=account_revision.run(c,'Q010-P030',**args,apply=True)
    review=t/'edited/account-amendments'/proof.ID/'revisions'/proof.REV/'review'
    final=json.loads((review/'result.json').read_text())
    fact_report=json.loads((review/'reviews/current/fact-check.json').read_text())
    assert next(r for r in fact_report['claims'] if r['id']=='scalar-storage')['basis']==basis
    if basis=='papers':
        assert 'review_required' in result
        assert 'does not match its evidence' in final['reason']
        assert [r['role'] for r in calls]==['author','archivist','fact-checker']
        return
    assert 'accepted;' in result and len(calls)==5
    assert final['basis']['papers']==0 and final['basis']['research record']>0
    assert (review.parent/'build/paper.pdf').exists()
    for call in calls:
        assert 'OFFLINE TEST FIXTURE' not in call['prompt']
        if call['role']=='archivist':
            shown=json.loads(call['prompt'].split('Allowed input files:\n',1)[1])
            assert 'scalar-storage' in shown['claims/current.json']
            assert 'not scientific claims' in shown['brief.md']
            assert not any(n.startswith('sources/') for n in shown)
        if call['role']=='critic':
            shown=json.loads(call['prompt'].split('Allowed input files:\n',1)[1])
            assert source in shown
            assert 'retained campaign research records' in shown['brief.md']
            assert not any(n.startswith(('sources/internal/','reviews/','revisions/')) for n in shown)
    claims=json.loads((review/'claims/current.json').read_text())
    assert all('contract_sha256' not in r['text'] and 'approval_reference' not in r['text'] for r in claims)
