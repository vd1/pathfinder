import json
import pytest
from pathfinder import whole_bodies as w


def expected(files):return {n:w.sha(v) for n,v in files.items()}

def test_whole_groups_and_injection_unicode():
 text='α😀\r\nRAW 99 30\nCOPY 0 1 2\nEND FILE\nRefitting with full qualification'+('z'*9000)
 files={'drafts/current.tex':text,'sources/internal/baseline.tex':text,'claims/current.json':json.dumps([{'text':text}]),'reviews/current/test.md':text+'report','sources/external/research-supplement.md':text*5}
 p,h,s=w.encode(files,'editor');assert w.decode(p,expected(files),'editor')==files
 assert w.encode(files,'editor')[0]==p
 for r in h['files']:
  if r['path']!='sources/external/research-supplement.md':
   assert len(r['segments'])==1 and 'literal' in r['segments'][0]
   assert files[r['path']] in p
 assert set(h['files'][0]['equivalent_paths'])=={'sources/internal/baseline.tex'} if h['files'][0]['path']=='drafts/current.tex' else True
 labels=[json.loads(line[5:]) for line in p.splitlines() if line.startswith('FILE {')]
 for group in labels:
  for r in group['equivalent_files']:
   assert r['chars']==len(files[r['path']]) and r['sha256']==w.sha(files[r['path']])

@pytest.mark.parametrize('kind',['scope','role','trailing','hash','length','unused','forward','copy-protected','header'])
def test_reject(kind,monkeypatch):
 files={'drafts/current.tex':'abcdef'*1000,'sources/external/research-supplement.md':'abcdef'*10000}
 p,h,s=w.encode(files,'editor');e=expected(files);role='editor'
 if kind=='scope':e['hidden/review']='0'*64
 if kind=='role':role='critic'
 if kind=='trailing':p+='HIDDEN'
 if kind=='hash':p=p.replace(w.sha(files['drafts/current.tex']),'0'*64)
 if kind=='length':p=p.replace('"chars":6000','"chars":5999')
 if kind=='unused':p=p.replace('"groups":2','"groups":3')+'RAW 99 6\nHIDDEN\n'
 if kind=='forward':
  import re
  p=re.sub(r'COPY \d+ ', 'COPY 99999 ', p, count=1)
 if kind=='copy-protected':p=p.replace('RAW 0 6000\n','COPY 999 0 6000\n',1)
 if kind=='header':
  monkeypatch.setattr(w,'MAX_HEADER',64);monkeypatch.setattr(w,'strict',lambda x:pytest.fail('parse before header bound'))
 with pytest.raises(ValueError):w.decode(p,e,role)


def test_expansion_before_allocation(monkeypatch):
 files={'a':'x'*6000,'b':'x'*6000};p,h,s=w.encode(files,'editor')
 assert len(p)<10000
 monkeypatch.setattr(w,'MAX_TOTAL',10000)
 with pytest.raises(ValueError,match='expansion'):w.decode(p,expected(files),'editor')


def test_role_local_and_empty():
 files={'sources/external/research-supplement.md':'abc'*12000,'a':'','b':'\r\n😀'}
 p,h,s=w.encode(files,'critic');assert w.decode(p,expected(files),'critic')==files
 bad,_,_=w.encode({**files,'reviews/hidden':'EXCLUDED'},'critic')
 with pytest.raises(ValueError):w.decode(bad,expected(files),'critic')
 assert s['probes']<=w.MAX_PROBES and s['comparisons']<=w.MAX_COMPARISONS and s['indexed']<=w.MAX_INDEX
