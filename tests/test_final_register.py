import pytest
from pathfinder import account_register as ar,pce


def test_superseded_and_surviving_claims_have_final_context():
    before='Old bound. Stable limitation.\n\nAnother paragraph.'
    changes=[{'finding':'first','before':'Old bound.','after':'Bound is 100.'},
             {'finding':'second','before':'Bound is 100.','after':'No quantitative bound is claimed.'}]
    candidate='No quantitative bound is claimed. Stable limitation.\n\nAnother paragraph.'
    r=ar.build(before,changes,candidate)
    assert r['records'][0]['status']=='superseded'
    assert [x['id'] for x in r['claims']]==['amendment-2']
    assert '100' not in str(r['claims'])


def test_partial_replacement_keeps_every_surviving_mandate_in_context():
    before='old\n\nUnchanged.'
    changes=[{'finding':'one','before':'old','after':'Keep X. Old Y.'},
             {'finding':'two','before':'Old Y.','after':'New Z.'}]
    r=ar.build(before,changes,'Keep X. New Z.\n\nUnchanged.')
    assert r['records'][0]['status']=='partially-superseded'
    assert r['claims'][0]['text']=='Keep X. New Z.'
    assert r['claims'][1]['text']=='New Z.'
    assert 'Old Y.' not in str(r['claims'])


def test_equal_text_elsewhere_does_not_resurrect_superseded_occurrence():
    r=ar.build('A.\n\nSame.',[{'finding':'one','before':'A.','after':'Same.'},
        {'finding':'two','before':'Same.\n\nSame.','after':'Withdrawn.\n\nSame.'}], 'Withdrawn.\n\nSame.')
    assert r['records'][0]['status']=='superseded'
    assert len(r['claims'])==1

@pytest.mark.parametrize('baseline,changes,candidate',[
    ('A A',[{'finding':'a','before':'A','after':'B'}],'B A'),
    ('A',[{'finding':'a','before':'A','after':'B'}],'C')])
def test_refuse_invalid_sequential_custody(baseline,changes,candidate):
    with pytest.raises(pce.Changed):ar.build(baseline,changes,candidate)

@pytest.mark.parametrize('tamper',['history','register','visible'])
def test_final_register_custody_rechecked_before_use(tmp_path,tamper):
    import json
    files={pce.BASELINE:'New.'};grant={}
    ar.attach(tmp_path,grant,files,'Old.',[{'finding':'f','before':'Old.','after':'New.'}],'New.')
    pce._write(tmp_path,'frozen-inputs.json',pce._json(files))
    assert ar.claims(tmp_path,grant,'New.')[0]['text']=='New.'
    if tamper=='visible':
        files['sources/internal/changes.json']=pce._json({'changes':[]})
        (tmp_path/'frozen-inputs.json').write_text(pce._json(files))
    else:
        path=tmp_path/('replacement-'+tamper+'.json')
        value=json.loads(path.read_text());value['unexpected']='tampered';path.write_text(pce._json(value))
    with pytest.raises(pce.Changed):ar.claims(tmp_path,grant,'New.')
