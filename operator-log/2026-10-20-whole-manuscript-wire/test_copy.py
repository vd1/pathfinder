"""Offline actual-account repair, five stub roles and real canonical build."""
import importlib.util,json,os
from pathlib import Path
import pytest
from pathfinder import account_wire,account_review,pce,pce_recovery,stub,transport,whole_bodies
HERE=Path(__file__).resolve().parent;REPO=HERE.parent.parent
spec=importlib.util.spec_from_file_location('helper',REPO/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
ID='floating-bound-definition-20261020';PAIR='Q053-P011'

def setup(tmp_path,monkeypatch):
 if os.environ.get("PATHFINDER_TEST_RUNTIME"):assert Path(pce.__file__).resolve().is_relative_to(Path(os.environ["PATHFINDER_TEST_RUNTIME"]))
 c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,PAIR,ID)
 root=t/'edited/account-amendments'/ID;prev=root/'review'
 args=dict(identity=ID,grant_id='whole-body-readability-1',failed_round_sha256=pce._sha(pce._json(pce_recovery.hashes(prev))),reason='One bounded independent whole-body readability repair; candidate and scientific inputs unchanged')
 return c,t,root,prev,args


def test_five_roles_build_preserve_resume(tmp_path,monkeypatch):
 c,t,root,prev,args=setup(tmp_path,monkeypatch);before=pce_recovery.hashes(t);calls=[];hold=[True]
 frozen=json.loads((prev/'frozen-inputs.json').read_text());candidate=(root/'candidate.tex').read_text()
 assert len(json.loads((root/'request.json').read_text())['changes']['changes'])==14
 out=account_wire.repair(c,PAIR,**args);assert 'prepared' in out
 target=account_review.workflow(root);grant=json.loads((target/'grant.json').read_text())
 assert json.loads((target/'frozen-inputs.json').read_text())==frozen
 assert (target/'replacement-register.json').read_bytes()==(prev/'replacement-register.json').read_bytes()
 visible_maps=[];visible=pce.visible
 def scoped(files,contract):
  m=visible(files,contract);visible_maps.append(m);return m
 monkeypatch.setattr(pce,'visible',scoped)
 def dispatch(c,pair,role,prompt,seconds=None):
  meta=json.loads((target/f'visibility/pass-01-{role}.json').read_text());payload=prompt.split('Allowed input files:\n',1)[1]
  shown=whole_bodies.decode(payload,meta['files_sha256'],role)
  expected=visible_maps[-1].copy()
  if role=='fact-checker':expected[pce.CLAIMS]=pce._json([{k:row[k]for k in ('id','text','kind','location') if k in row}for row in json.loads(expected[pce.CLAIMS])])
  assert shown==expected and pce._sha(payload)==meta['payload_sha256'] and pce._sha(prompt)==meta['prompt_sha256']
  assert len(prompt)<=1000000
  for frame in meta['file_frames']:
   if frame['path']!=pce.SUPPLEMENT:
    assert len(frame['segments'])==1 and 'literal' in frame['segments'][0]
    assert shown[frame['path']] in payload
  if pce.DRAFT in shown:
   assert candidate in payload
   for offset in (9191,24620,26621):assert candidate[offset-100:offset+100] in payload
  if role in ('fact-checker','critic'):assert not any(n.startswith(('reviews/','revisions/','sources/internal/'))for n in shown)
  if role=='editor' and hold[0]:raise pce.Stopped()
  calls.append(role)
  decoded=prompt.split('Allowed input files:\n',1)[0]+'Allowed input files:\n'+json.dumps(shown)
  return dict(role=role,outcome='completed',text=stub.pce_reply(c,role,decoded))
 monkeypatch.setattr(pce,'_dispatch',dispatch)
 with pytest.raises(pce.Stopped):account_wire.repair(c,PAIR,**args,apply=True)
 assert calls==['author','archivist','fact-checker','critic']
 retained=pce_recovery.hashes(target);hold[0]=False
 assert 'accepted;' in account_wire.repair(c,PAIR,**args,apply=True)
 assert calls==['author','archivist','fact-checker','critic','editor']
 assert (root/'build/paper.pdf').exists()
 assert all(pce_recovery.hashes(target)[n]==h for n,h in retained.items())
 after=pce_recovery.hashes(t);changed=[n for n,h in before.items()if after.get(n)!=h]
 assert changed==['edited/account-amendment.json'],changed
 assert (root/'candidate.tex').read_text()==candidate
 assert 'accepted;' in account_wire.repair(c,PAIR,**args,apply=True) and len(calls)==5
 assert json.loads((target/'result.json').read_text())['status']=='accepted'
 (HERE/'copy-proof.json').write_text(pce._json(dict(preserved_files=len(before)-1,calls=calls,changed=changed,failed_round_files=len(pce_recovery.hashes(prev)),real_pdf=True,candidate_sha256=pce._sha(candidate),register_records=14,first_author=grant['review_wire']['first_author']['prompt_chars'])))

@pytest.mark.parametrize('mutation',['receipt','candidate','scope','codec','packet','allowance','register','cap','second','digest'])
def test_refusal(tmp_path,monkeypatch,mutation):
 c,t,root,prev,args=setup(tmp_path,monkeypatch)
 if mutation=='digest':
  args['failed_round_sha256']='0'*64
 else:account_wire.repair(c,PAIR,**args)
 target=account_review.workflow(root)
 if mutation=='receipt':
  path=next((prev/'dispatch').glob('*.json'));path.write_text(path.read_text()+' ')
 if mutation=='candidate':(root/'candidate.tex').write_text('changed')
 if mutation in ('scope','codec','packet','allowance'):
  path=target/'grant.json';g=json.loads(path.read_text())
  if mutation=='scope':g['review_wire']['scope_policy']='bad'
  if mutation=='codec':g['review_wire']['codec_sha256']='0'*64
  if mutation=='packet':g['review_wire']['first_author']['prompt_sha256']='0'*64
  if mutation=='allowance':g['settings']['passes']=2
  path.write_text(pce._json(g))
 if mutation=='register':(target/'replacement-register.json').write_text('{}')
 if mutation=='cap':monkeypatch.setattr(transport,'max_prompt_chars',lambda c:800000)
 if mutation=='second':args['grant_id']='second'
 monkeypatch.setattr(pce,'_dispatch',lambda *a,**kw:pytest.fail('no dispatch'))
 with pytest.raises(pce.Changed):account_wire.repair(c,PAIR,**args,apply=True)


def test_prep_boundary_no_writes(tmp_path,monkeypatch):
 c,t,root,prev,args=setup(tmp_path,monkeypatch);files=json.loads((prev/'frozen-inputs.json').read_text())
 d=whole_bodies.declaration(files,1000000,c);boundary=d['reserved_prompt_chars']
 assert whole_bodies.declaration(files,boundary,c)['reserved_prompt_chars']==boundary
 before=pce_recovery.hashes(t)
 monkeypatch.setattr(transport,'max_prompt_chars',lambda c:boundary-1)
 with pytest.raises(pce.Changed,match='reserve exceeds'):account_wire.repair(c,PAIR,**args)
 assert pce_recovery.hashes(t)==before


def test_generated_editor_growth_refuses_without_dispatch(tmp_path,monkeypatch):
 import random,string
 c,t,root,prev,args=setup(tmp_path,monkeypatch);calls=[]
 selected=(t/'edited/account-amendment.json').read_bytes()
 def dispatch(c,pair,role,prompt,seconds=None):
  assert role!='editor','over-cap editor must not dispatch'
  target=account_review.workflow(root);meta=json.loads((target/f'visibility/pass-01-{role}.json').read_text())
  shown=whole_bodies.decode(prompt.split('Allowed input files:\n',1)[1],meta['files_sha256'],role)
  decoded=prompt.split('Allowed input files:\n',1)[0]+'Allowed input files:\n'+json.dumps(shown)
  reply=json.loads(stub.pce_reply(c,role,decoded));calls.append(role)
  if role=='critic':
   noise=''.join(random.Random(83).choices(string.ascii_letters+string.digits,k=300000))
   for name in reply['files']:reply['files'][name]+='\nCapacity fixture: '+noise+'\n'
  return dict(role=role,outcome='completed',text=json.dumps(reply))
 monkeypatch.setattr(pce,'_dispatch',dispatch)
 with pytest.raises(pce.Changed,match='complete review context exceeds'):
  account_wire.repair(c,PAIR,**args,apply=True)
 assert calls==['author','archivist','fact-checker','critic']
 assert not (account_review.workflow(root)/'dispatch/pass-01-editor.json').exists()
 assert (t/'edited/account-amendment.json').read_bytes()==selected
