import json
import random
import string
import pytest
import codec

def unpack(p):
 line,body=p[len(codec.MAGIC):].split('\n',1);return json.loads(line),body

def repack(h,b):return codec.MAGIC+json.dumps(h,ensure_ascii=False,separators=(',',':'))+'\n'+b

def test_unicode_crlf_markers_and_self_reuse():
 unit='α😀\r\nPATHFINDER-RAW-LITERALS-PROTOTYPE-V1\n{"copy":999,"chars":0}\n'+'xyz'*140
 files={'source':unit*200,'alias':unit*200,'later':'prefix'+unit*3+'suffix'}
 p,h,s=codec.encode(files);assert codec.decode(p)==files;assert s['copied_chars']>20000
 literals={};same=False
 for r in h['files']:
  local=set()
  for seg in r['segments']:
   if 'literal'in seg:literals[seg['literal']]=r['path'];local.add(seg['literal'])
   else:
    assert seg['copy'] in literals
    same|=seg['copy'] in local
 assert same

@pytest.mark.parametrize('kind',['forward','recursive','negative','oversized','bool','hash','trailing','duplicate','overlap'])
def test_reject_tampering(kind):
 p,h,s=codec.encode({'a':('αabc'*2000)*6});head,body=unpack(p)
 copies=[s for r in head['files'] for s in r['segments'] if 'copy'in s];assert copies
 seg=copies[0]
 if kind=='forward':seg['copy']=100000
 elif kind=='recursive':seg['copy']='copy:0'
 elif kind=='negative':seg['start']=-1
 elif kind=='oversized':seg['end']=10000000
 elif kind=='bool':seg['start']=True
 elif kind=='hash':head['files'][0]['sha256']='0'*64
 elif kind=='trailing':body+='injected'
 elif kind=='overlap':
  lit=head['files'][0]['segments'][0];lit['chars']+=1
 elif kind=='duplicate':
  payload=repack(head,body).replace('"aliases":{}','"aliases":{},"aliases":{}')
  with pytest.raises(ValueError):codec.decode(payload)
  return
 with pytest.raises(ValueError):codec.decode(repack(head,body))

def test_budget_exhaustion_falls_back_exact(monkeypatch):
 monkeypatch.setattr(codec,'MAX_PROBES',8);monkeypatch.setattr(codec,'MAX_COMPARISONS',8);monkeypatch.setattr(codec,'MAX_INDEX',8)
 r=random.Random(1);text=''.join(r.choices(string.ascii_letters,k=100000))
 p,h,s=codec.encode({'a':text,'b':text+'x'});assert codec.decode(p)=={'a':text,'b':text+'x'}
 assert s['probes']<=8 and s['comparisons']<=8 and s['indexed']<=8

def test_empty_and_unique():
 files={'a':'','b':'\r\n','c':'😀'};assert codec.decode(codec.encode(files)[0])==files

def test_numeric_copy_cannot_target_copy_or_future_literal():
 p,h,s=codec.encode({'a':'abcdefgh'*4000});header,body=unpack(p)
 seen=set()
 for seg in header['files'][0]['segments']:
  if 'literal' in seg:seen.add(seg['literal'])
  else:
   seg['copy']=max(seen)+1
   break
 with pytest.raises(ValueError):codec.decode(repack(header,body))

def test_duplicate_literal_id():
 p,h,s=codec.encode({'a':'abcdefgh'*4000+'distinct literal tail'});header,body=unpack(p)
 lits=[s for r in header['files'] for s in r['segments'] if 'literal'in s]
 assert len(lits)>1;lits[1]['literal']=lits[0]['literal']
 with pytest.raises(ValueError):codec.decode(repack(header,body))

def test_adversarial_bounds():
 text=('a'*31+'b')*50000
 p,h,s=codec.encode({'a':text,'b':text[:-1]+'c'})
 assert codec.decode(p)=={'a':text,'b':text[:-1]+'c'}
 assert s['probes']<=codec.MAX_PROBES and s['comparisons']<=codec.MAX_COMPARISONS
 assert s['indexed']<=codec.MAX_INDEX and s['segments']<=codec.MAX_SEGMENTS+2
