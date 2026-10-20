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
