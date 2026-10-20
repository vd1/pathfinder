import json
import pytest
from pathfinder import editor_packet as ep


def fixture():
    start='α line\r\n'*200;end='end 😀\n'*200
    return {'a.tex':start+'INSERT'+end,'b.tex':start+end,'c.tex':start+end,
            'd.json':'{"marker":"PATHFINDER-EDITOR-SPANS-V1\\n"}\n','empty':''}


def test_lossless_unicode_aliases_and_exact_spans():
    files=fixture();payload,header=ep.encode_spans(files)
    assert ep.decode_spans(payload)==files
    row=next(r for r in header['files'] if r['path']=='b.tex')
    assert all('copy' in s for s in row['segments'])
    assert header['aliases']=={'c.tex':'b.tex'}
    assert ep.encode_spans(files)[0]==payload


@pytest.mark.parametrize('bad',['forward','negative','overrun','boolean','file-hash','literal-hash','literal-length','duplicate','trailing','alias','segment','file-count'])
def test_rejects_nonlossless_spans(bad):
    payload,header=ep.encode_spans(fixture());body=payload[len(ep.SPAN_MAGIC):].partition('\n')[2]
    a,b=header['files'][:2]
    if bad=='forward':b['segments'][0]['copy']='missing'
    if bad=='negative':b['segments'][0]['start']=-1
    if bad=='overrun':b['segments'][0]['end']=10**9
    if bad=='boolean':b['segments'][0]['start']=False
    if bad=='file-hash':b['sha256']='0'*64
    if bad=='literal-hash':a['segments'][0]['sha256']='0'*64
    if bad=='literal-length':a['segments'][0]['chars']+=1
    if bad=='duplicate':b['path']=a['path']
    if bad=='trailing':body+='x'
    if bad=='alias':header['aliases']['c.tex']='absent'
    if bad=='segment':b['segments'][0]['extra']=True
    if bad=='file-count':b['chars']+=1
    broken=ep.SPAN_MAGIC+json.dumps(header)+'\n'+body
    with pytest.raises(ValueError):ep.decode_spans(broken)
