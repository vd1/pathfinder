import copy,json
import pytest
from pathfinder import account_bibliography as ab,pce,paper

BIB='''@misc{Q,
 author = {A},
 title = {Exact title},
 year = {2021},
 doi = {10.1/q},
 note = {Conflicting date}
}
@misc{L,
 author = {B},
 doi = {10.1/l},
 note = {Old audit}
}
'''
def fixture():
    ops=[dict(key='Q',doi='10.1/q',operation='registry-year',evidence='q',quote='Exact title',old_note='Conflicting date'),dict(key='L',doi='10.1/l',operation='supply-missing-title',evidence='l',quote='New exact title')]
    evidence={'q':{'text':json.dumps({'status':'ok','message':{'DOI':'10.1/q','title':['Exact title'],'published':{'date-parts':[[2026,7,22]]}}})},'l':{'text':json.dumps({'doi':'10.1/l','title':'New exact title'})}}
    return ops,evidence

def test_exact_metadata_only():
    ops,e=fixture();b=paper.bib_entries(ab.transform(BIB,ops,e));a=paper.bib_entries(BIB)
    assert b['Q']=={k:('2026' if k=='year' else v) for k,v in a['Q'].items() if k!='note'}
    assert b['L']=={**a['L'],'title':'New exact title'}
    assert 'title = {New exact title},' in ab.transform(BIB,ops,e)

@pytest.mark.parametrize('change',['doi','title','date','status','note','duplicate','existing-title'])
def test_refuses_unbound_metadata(change):
    ops,e=fixture();b=BIB;r=json.loads(e['q']['text'])
    if change=='doi':r['message']['DOI']='10.1/other'
    if change=='title':r['message']['title']=['Something else']
    if change=='date':r['message']['published']['date-parts']=[[2026]]
    if change=='status':r['status']='error'
    if change=='note':ops[0]['old_note']='different'
    if change=='duplicate':ops.append(copy.deepcopy(ops[0]))
    if change=='existing-title':b=b.replace('author = {B},','author = {B},\n title = {Existing},')
    e['q']['text']=json.dumps(r)
    with pytest.raises(pce.Changed):ab.transform(b,ops,e)
