import json
import random
import string
import pytest
from pathfinder import raw_literals as codec

def expected(files):return {n:codec.sha(t) for n,t in files.items()}
def enc(files):return codec.encode(files,'critic')
def dec(payload,files):return codec.decode(payload,expected(files),'critic')
def unpack(p):
 line,body=p[len(codec.MAGIC):].split('\n',1);return json.loads(line),body
def repack(h,b):return codec.MAGIC+json.dumps(h,ensure_ascii=False,separators=(',',':'))+'\n'+b

def test_scope_roundtrip_unicode_crlf_injection():
 unit='α😀\r\nPATHFINDER-RAW-LITERALS-V1\n{"copy":999,"chars":0}\n'+'xyz'*140
 files={'source':unit*200,'alias':unit*200,'later':'prefix'+unit*3+'suffix'}
 p,h,s=enc(files);assert dec(p,files)==files;assert s['copied_chars']>20000
 roots={};within=False
 for r in h['files']:
  local=set()
  for seg in r['segments']:
   if 'literal'in seg:roots[seg['literal']]=r['path'];local.add(seg['literal'])
   else:assert seg['copy'] in roots;within|=seg['copy'] in local
 assert within

@pytest.mark.parametrize('kind',['forward','recursive','negative','oversized','bool','hash','trailing','duplicate','length','unused','cross-role'])
def test_reject_tampering(kind):
 files={'a':('αabc'*2000)*6};p,h,s=enc(files);head,body=unpack(p)
 seg=next(s for r in head['files'] for s in r['segments'] if 'copy'in s)
 if kind=='forward':seg['copy']=100000
 elif kind=='recursive':seg['copy']='copy:0'
 elif kind=='negative':seg['start']=-1
 elif kind=='oversized':seg['end']=10000000
 elif kind=='bool':seg['start']=True
 elif kind=='hash':head['files'][0]['sha256']='0'*64
 elif kind=='trailing':body+='injected'
 elif kind=='length':head['files'][0]['segments'][0]['chars']+=1
 elif kind=='unused':head['unused_literals']=[{'literal':99,'text':'EXCLUDED REVIEW'}]
 elif kind=='cross-role':
  # Even a correctly self-hashed packet cannot introduce another role's material.
  malicious={**files,'reviews/hidden.md':'EXCLUDED REVIEW'};p,_,_=enc(malicious)
  with pytest.raises(ValueError):dec(p,files)
  return
 elif kind=='duplicate':
  payload=repack(head,body).replace('"aliases":{}','"aliases":{},"aliases":{}')
  with pytest.raises(ValueError):dec(payload,files)
  return
 with pytest.raises(ValueError):dec(repack(head,body),files)

def test_budget_exhaustion_exact(monkeypatch):
 monkeypatch.setattr(codec,'MAX_PROBES',8);monkeypatch.setattr(codec,'MAX_COMPARISONS',8);monkeypatch.setattr(codec,'MAX_INDEX',8)
 r=random.Random(1);text=''.join(r.choices(string.ascii_letters,k=100000));files={'a':text,'b':text+'x'}
 p,h,s=enc(files);assert dec(p,files)==files
 assert s['probes']<=8 and s['comparisons']<=8 and s['indexed']<=8

def test_copy_never_has_identity_and_unused_body_refused():
 files={'a':'abcdefgh'*4000};p,h,s=enc(files);head,body=unpack(p)
 seen=set()
 for seg in head['files'][0]['segments']:
  if 'literal' in seg:seen.add(seg['literal'])
  else:seg['copy']=max(seen)+1;break
 with pytest.raises(ValueError):dec(repack(head,body),files)
 with pytest.raises(ValueError):dec(p+'EXCLUDED ADMIN',files)

def test_duplicate_literal_and_empty():
 files={'a':'abcdefgh'*4000+'distinct tail'};p,h,s=enc(files);head,body=unpack(p)
 lits=[s for r in head['files'] for s in r['segments'] if 'literal'in s]
 lits[1]['literal']=lits[0]['literal']
 with pytest.raises(ValueError):dec(repack(head,body),files)
 empty={'a':'','b':'\r\n','c':'😀'};assert dec(enc(empty)[0],empty)==empty

def test_adversarial_bounds():
 text=('a'*31+'b')*50000;files={'a':text,'b':text[:-1]+'c'}
 p,h,s=enc(files);assert dec(p,files)==files
 assert s['probes']<=codec.MAX_PROBES and s['comparisons']<=codec.MAX_COMPARISONS
 assert s['indexed']<=codec.MAX_INDEX and s['segments']<=codec.MAX_SEGMENTS+2

def test_scope_owner_not_evidence_status():
 files={'historical/source':'x'*10000,'current/source':'x'*10000}
 p,h,s=enc(files);assert dec(p,files)==files
 assert set(h['aliases'])|{r['path'] for r in h['files']}==set(files)
 with pytest.raises(ValueError):codec.decode(p,expected(files),'editor')

def test_header_rejected_before_json_parse(monkeypatch):
 monkeypatch.setattr(codec,'MAX_HEADER',64)
 monkeypatch.setattr(codec,'strict',lambda s:pytest.fail('must reject before JSON parse'))
 with pytest.raises(ValueError,match='header length'):
  codec.decode(codec.MAGIC+' '*65+'\n',{},'critic')

def test_cumulative_expansion_before_copy_and_join(monkeypatch):
 files={'a':'abcdefgh'*1000,'b':'abcdefgh'*1000+'x'};p,h,s=enc(files)
 # Input framing still fits this bound, but the declared second file exceeds cumulative expansion.
 assert len(p)<12000
 monkeypatch.setattr(codec,'MAX_TOTAL',12000)
 with pytest.raises(ValueError,match='size'):
  dec(p,files)

def test_copy_preallocation_uses_declared_remaining_length():
 files={'a':'abcdefgh'*4000};p,h,s=enc(files);head,body=unpack(p)
 first=head['files'][0]['segments'][0]['chars'];head['files'][0]['chars']=first+1
 with pytest.raises(ValueError,match='copy expansion'):
  dec(repack(head,body),files)
