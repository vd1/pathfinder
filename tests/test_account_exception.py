import pytest
from pathfinder import account_exception as ex, pce


def test_projection_exact_values_and_complete_omitted_ranges():
    data={'a/~': [{'v':'α\r\n'}, {'v':2}, {'v':3}], 'empty':{}, 'extra':[False,None]}
    selected, omitted=ex.project(data,['/a~1~0/1/v'])
    assert selected=={'/a~1~0/1/v':2}
    assert omitted==[
        {'array_pointer':'/a~1~0','start':0,'end_exclusive':1,
         'canonical_json_sha256':ex.digest([{'v':'α\r\n'}]),
         'canonical_json_bytes':len(ex.canonical([{'v':'α\r\n'}]).encode())},
        {'array_pointer':'/a~1~0','start':2,'end_exclusive':3,
         'canonical_json_sha256':ex.digest([{'v':3}]),'canonical_json_bytes':9},
        {'pointer':'/empty','canonical_json_sha256':ex.digest({}),'canonical_json_bytes':2},
        {'pointer':'/extra','canonical_json_sha256':ex.digest([False,None]),'canonical_json_bytes':12}]


@pytest.mark.parametrize('pointers', [
    ['/a','/a/0'], ['/a/0','/a/0'], ['/a/00'], ['/a/-1'], ['/a/+1'], ['/a/~2'],
    [''], [], ['/a/１'], [None]])
def test_invalid_or_overlapping_pointers(pointers):
    with pytest.raises((pce.Changed, KeyError, IndexError)):
        ex.project({'a':[1,2]},pointers)


@pytest.mark.parametrize('text',['{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}'])
def test_no_ambiguous_json(text):
    with pytest.raises(ValueError):ex._load(text)


def test_projection_changes_if_omitted_content_changes():
    first={'a':[1,2],'b':'α\r\n'}
    second={'a':[1,2],'b':'α\n'}
    a,omitted_a=ex.project(first,['/a/0'])
    b,omitted_b=ex.project(second,['/a/0'])
    assert a==b and omitted_a!=omitted_b


def test_legacy_23_contract_remains_exact(tmp_path):
    import json
    delta = dict(parent_candidate_sha256='a', parent_acceptance_sha256='b', returned_findings_sha256='c',
                 changes=[dict(finding=f'P{i}', before=str(i), after=str(i+1)) for i in (1,2,3)])
    c = dict(version=1, pair='Q1P1', identity='test', parent_pointer={'id':'prior'},
             parent_request_sha256='request', parent_frozen_inputs_sha256='inputs',
             parent_candidate_sha256='a', parent_acceptance_sha256='b', returned_findings_sha256='c',
             candidate_sha256=pce._sha('candidate'), delta_sha256=ex.digest(delta),
             original_baseline_sha256='original', cumulative_sha256='cumulative',
             existing_count=20, total_count=23, finding_ids=['P1','P2','P3'], selected_json={})
    packet=tmp_path/'packet';packet.mkdir();contract=packet/'history-exception.json'
    contract.write_text(json.dumps(c));approval=tmp_path/'test-approval.json'
    receipt=dict(version=1,decision='approve',authority='owner',approved_by='TEST ONLY',
                 approval_reference='unit fixture',contract_sha256=ex.digest(c))
    approval.write_text(json.dumps(receipt))
    assert ex.authorize(packet,approval,'Q1P1','test',delta,'candidate')['contract']==c
    c['total_count']=24;contract.write_text(json.dumps(c))
    receipt['contract_sha256']=ex.digest(c);approval.write_text(json.dumps(receipt))
    with pytest.raises(pce.Changed,match='binding differs'):
        ex.authorize(packet,approval,'Q1P1','test',delta,'candidate')
