"""Copy-only receipt reuse: a pending editor never repeats the four completed roles."""
import importlib.util,json,os
from pathlib import Path
import pytest
from pathfinder import account_successor,pce,pce_recovery,transport
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder');PACK=ROOT/'operator-log/2026-10-20-affinity-record-specifications'
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
@pytest.mark.parametrize('mode',['resume','cap','interrupted'])
def test_pending(tmp_path,monkeypatch,mode):
 assert Path(pce.__file__).resolve().is_relative_to(Path(os.environ.get('PATHFINDER_TEST_RUNTIME',str(ROOT))))
 c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q053-P011','scalar-allowance-definition-20261020')
 calls=script(monkeypatch,c);dispatch=pce._dispatch
 class Pending(Exception):pass
 def stop(c,pair,role,prompt,**kw):
  if role=='editor':raise Pending()
  return dispatch(c,pair,role,prompt,**kw)
 monkeypatch.setattr(pce,'_dispatch',stop)
 args=dict(identity='feature-record-specifications-20261020',packet=PACK/'Q053-P011',reason='Private transport-only successor copy',apply=True)
 with pytest.raises(Pending):account_successor.run(c,'Q053-P011',**args)
 assert len(calls)==4
 root=t/'edited/account-amendments/feature-record-specifications-20261020';review=root/'review'
 before=pce_recovery.hashes(t/'edited');prior=pce_recovery.hashes(review)
 assert len(list((review/'dispatch').glob('*.json')))==4
 monkeypatch.setattr(pce,'_dispatch',dispatch)
 if mode=='cap':
  cc=__import__('copy').copy(c);cc._pce_workflow=review
  monkeypatch.setattr(transport,'max_prompt_chars',lambda c:1000)
  with pytest.raises(pce.Changed):pce.run(cc,'Q053-P011')
  assert len(calls)==4 and pce_recovery.hashes(t/'edited')==before
  return
 if mode=='interrupted':
  write=pce._write
  def interrupt(path,name,text,**kw):
   if name=='result.json':raise Pending()
   return write(path,name,text,**kw)
  monkeypatch.setattr(pce,'_write',interrupt)
  with pytest.raises(Pending):account_successor.run(c,'Q053-P011',**args)
  assert len(calls)==5
  monkeypatch.setattr(pce,'_write',write)
 assert 'accepted;' in account_successor.run(c,'Q053-P011',**args)
 assert len(calls)==5 and (root/'build/paper.pdf').exists()
 after=pce_recovery.hashes(review)
 assert all(after[k]==v for k,v in prior.items())
 all_after=pce_recovery.hashes(t/'edited')
 assert all(all_after[k]==v for k,v in before.items() if k not in ('account-amendment.json','account-successor.json'))
 assert 'accepted;' in account_successor.run(c,'Q053-P011',**args) and len(calls)==5
 print(mode,'preserved',len(prior),'pending workflow files; four roles unchanged, editor only; real build')
