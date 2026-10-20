"""Actual copied account, no model calls; canonical role packet and build proofs."""
import importlib.util
import json
import os
import shutil
from pathlib import Path
import pytest
from pathfinder import account_successor, pce, pce_recovery, raw_literals, stub, transport
ROOT=Path('/Users/v/Code_2026/pathfinder');HERE=Path(__file__).resolve().parent;PACK=HERE/'Q053-P011'
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
IDENTITY='floating-bound-definition-20261020'

def setup(tmp_path,monkeypatch):
 if os.environ.get('PATHFINDER_TEST_RUNTIME'):assert Path(pce.__file__).resolve().is_relative_to(Path(os.environ['PATHFINDER_TEST_RUNTIME']))
 c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q053-P011','feature-record-specifications-20261020')
 for row in json.loads((PACK/'successor.json').read_text())['evidence_projection']['include']:
  dest=t/row['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(helper.BASE/'threads/Q053-P011'/row['path'],dest)
 return c,t,dict(identity=IDENTITY,packet=PACK,reason='Bounded P1 retained floating-bound definition; fresh raw-literal-v1 strict review under authorised completion scope')

def decode_prompt(prompt,role):
 payload=prompt.split('Allowed input files:\n',1)[1];header=json.loads(payload[len(raw_literals.MAGIC):].split('\n',1)[0]);hashes={r['path']:r['sha256'] for r in header['files']}
 hashes.update({n:hashes[target] for n,target in header['aliases'].items()})
 return raw_literals.decode(payload,hashes,role)

def test_five_real_role_prompts_resume_build_and_preservation(tmp_path,monkeypatch):
 c,t,args=setup(tmp_path,monkeypatch);before=pce_recovery.hashes(t);calls=[];hold=[True]
 parent=t/'edited/account-amendments/feature-record-specifications-20261020/review';old=json.loads((parent/'frozen-inputs.json').read_text())
 root=t/'edited/account-amendments'/IDENTITY;review=root/'review'
 visible_maps=[];original_visible=pce.visible
 def scoped(files,contract):
  value=original_visible(files,contract);visible_maps.append(dict(value));return value
 monkeypatch.setattr(pce,'visible',scoped)
 def dispatch(c,pair,role,prompt,seconds=None):
  shown=decode_prompt(prompt,role)
  expected=dict(visible_maps[-1])
  if role=='fact-checker' and pce.CLAIMS in expected:
   expected[pce.CLAIMS]=pce._json([{k:claim[k] for k in ('id','text','kind','location') if k in claim} for claim in json.loads(expected[pce.CLAIMS])])
  assert shown==expected
  assert len(prompt)<=transport.max_prompt_chars(c)
  visibility=json.loads((review/f'visibility/pass-01-{role}.json').read_text())
  assert visibility['prompt_sha256']==pce._sha(prompt) and visibility['prompt_chars']==len(prompt)
  assert visibility['expanded_files_sha256']=={n:pce._sha(v) for n,v in sorted(shown.items())}
  # Only this role's visible mapping can contribute raw literals; decoder refuses any extra roots.
  if role in ('critic','fact-checker'):
   assert not any(n.startswith(('reviews/','revisions/','sources/internal/')) for n in shown)
  if role=='archivist':assert not any(n.startswith('sources/') for n in shown)
  else:
   for k,v in old.items():
    if k.startswith('sources/external/'):assert shown[k]==v
   for row in json.loads((PACK/'successor.json').read_text())['evidence_projection']['include']:
    key='sources/external/amendment-retained-'+pce._sha(row['path'])[:16]+'.txt'
    assert shown[key].endswith((t/row['path']).read_bytes().decode())
  if role=='editor' and hold[0]:raise pce.Stopped()
  calls.append(dict(role=role,prompt=prompt))
  # Stub consumes the decoded permitted map; production prompt itself is retained above.
  decoded=prompt.split('Allowed input files:\n',1)[0]+'Allowed input files:\n'+json.dumps(shown)
  reply=json.loads(stub.pce_reply(c,role,decoded))
  if role=='author':
   claims=json.loads(reply['files'][pce.CLAIMS]);claims.append(dict(id='retained-milp-definition',text='The retained runner derives upper bounds from the negative minimisation dual bound.',kind='fact',location='P1',status='needs-review'));reply['files'][pce.CLAIMS]=pce._json(claims)
  if role=='fact-checker':
   source=next(n for n in shown if n.startswith('sources/external/amendment-retained-') and 'distance_only_big.py' in shown[n])
   for name,text in reply['files'].items():
    report=json.loads(text);claim=next(r for r in report['claims'] if r['id']=='retained-milp-definition');claim['basis']='research record';claim['evidence']=[source+'#solver'];reply['files'][name]=pce._json(report)
  return {'role':role,'outcome':'completed','text':json.dumps(reply)}
 monkeypatch.setattr(pce,'_dispatch',dispatch)
 with pytest.raises(pce.Stopped):account_successor.run(c,'Q053-P011',**args,apply=True)
 assert [r['role']for r in calls]==['author','archivist','fact-checker','critic']
 retained=pce_recovery.hashes(review);assert not (review/'dispatch/pass-01-editor.json').exists()
 hold[0]=False;out=account_successor.run(c,'Q053-P011',**args,apply=True)
 assert 'accepted;' in out and len(calls)==5 and (root/'build/paper.pdf').exists()
 assert all(pce_recovery.hashes(review)[n]==h for n,h in retained.items())
 after=pce_recovery.hashes(t)
 changed=[n for n,h in before.items() if after.get(n)!=h]
 assert set(changed)<= {'edited/account-amendment.json','edited/account-successor.json'}, changed
 assert all(json.loads((t/n).read_text())=={'id':IDENTITY} for n in changed)
 assert 'accepted;' in account_successor.run(c,'Q053-P011',**args,apply=True) and len(calls)==5
 grant=json.loads((review/'grant.json').read_text());files=json.loads((review/'frozen-inputs.json').read_text())
 assert grant['review_wire']==raw_literals.declaration(files,1000000,c)
 assert grant['review_wire']['reserved_prompt_chars']<1000000
 assert grant['review_wire']['first_author']['prompt_sha256']==pce._sha(calls[0]['prompt'])
 assert len(json.loads((root/'request.json').read_text())['changes']['changes'])==14
 assert grant['settings']['passes']==grant['settings']['fact_checks']==1 and 'pass_score' not in grant['settings']['critic']
 print('Five role packets, pending-editor-only resume, real build; preserved',len(before),'pre-existing files')
 # Measure complete real parent reports, including archivist, under the actual canonical editor head.
 actual=json.loads((parent/'visibility/pass-01-editor.json').read_text());shown={}
 candidate=(PACK/'account-candidate.tex').read_text()
 for name in actual['files_sha256']:
  if name in files:shown[name]=files[name]
  elif name.endswith('.tex'):shown[name]=candidate
  else:shown[name]=(parent/name).read_bytes().decode()
 shown.update({k:v for k,v in files.items() if k.startswith('sources/external/amendment-retained-')})
 head=calls[-1]['prompt'].removeprefix(raw_literals.INSTRUCTION).split('Allowed input files:\n',1)[0]+'Allowed input files:\n'
 prompt,meta=raw_literals.packet(head,shown,'editor');assert len(prompt)<1000000
 import random,string
 stress=[]
 for n in [8192,32768]:
  rng=random.Random(73);noise=''.join(rng.choices(string.ascii_letters+string.digits,k=n));m=dict(shown)
  fact=json.loads(m['reviews/current/fact-check.json']);fact['offline_capacity_stress_note']=noise
  for k in list(m):
   if k.startswith('reviews/') and k.endswith('fact-check.json'):m[k]=pce._json(fact)
   if k.startswith('revisions/') and k.endswith('evidence-diff.json'):
    arch=json.loads(m[k]);arch['fact_check']=fact;m[k]=pce._json(arch)
  s,sm=raw_literals.packet(head,m,'editor');assert len(s)<1000000;stress.append(dict(note_chars=n,prompt_chars=len(s),metadata=sm))
 (HERE/'actual-profile.json').write_text(pce._json(dict(preparation=grant['review_wire'],actual_editor=meta,stress=stress,
  stub_role_prompt_chars={r['role']:len(r['prompt'])for r in calls},preserved_preexisting_files=len(before))))
 print('Actual editor',len(prompt),'stress',[s['prompt_chars']for s in stress])

@pytest.mark.parametrize('mutation',['codec','scope','remove','input','packet','first-author','cap','remove-both'])
def test_mutation_refuses_before_call(tmp_path,monkeypatch,mutation):
 c,t,args=setup(tmp_path,monkeypatch);account_successor.run(c,'Q053-P011',**args)
 r=t/'edited/account-amendments'/IDENTITY/'review';g=json.loads((r/'grant.json').read_text())
 if mutation=='codec':g['review_wire']['codec_sha256']='0'*64
 if mutation=='scope':g['review_wire']['scope_policy']='all-grant'
 if mutation=='remove':g.pop('review_wire')
 if mutation=='remove-both':
  g.pop('review_wire');(r/'wire-declaration.json').unlink()
 if mutation=='packet':g['review_wire']['preparation']['prompt_sha256']='0'*64
 if mutation=='first-author':g['review_wire']['first_author']['prompt_sha256']='0'*64
 if mutation=='cap':monkeypatch.setattr(transport,'max_prompt_chars',lambda c:1000001)
 if mutation=='input':
  f=json.loads((r/'frozen-inputs.json').read_text());f['brief.md']+='CHANGED';(r/'frozen-inputs.json').write_text(json.dumps(f))
 (r/'grant.json').write_text(json.dumps(g));monkeypatch.setattr(pce,'_dispatch',lambda *a,**kw:pytest.fail('no calls'))
 with pytest.raises(pce.Changed):account_successor.run(c,'Q053-P011',**args,apply=True)


def test_no_opt_in_preserves_legacy_refusal(tmp_path,monkeypatch):
 c,t,args=setup(tmp_path,monkeypatch);args['packet']=ROOT/'operator-log/2026-10-20-affinity-floating-bounds/Q053-P011';before=pce_recovery.hashes(t)
 with pytest.raises(pce.Changed,match='complete successor evidence exceeds'):account_successor.run(c,'Q053-P011',**args)
 assert pce_recovery.hashes(t)==before

def test_actual_packet_binding_mutation_refuses_resume(tmp_path,monkeypatch):
 c,t,args=setup(tmp_path,monkeypatch)
 def pause(*a,**kw):raise pce.Stopped()
 monkeypatch.setattr(pce,'_dispatch',pause)
 with pytest.raises(pce.Stopped):account_successor.run(c,'Q053-P011',**args,apply=True)
 path=t/'edited/account-amendments'/IDENTITY/'review/visibility/pass-01-author.json'
 value=json.loads(path.read_text());value['payload_sha256']='0'*64;path.write_text(pce._json(value))
 monkeypatch.setattr(pce,'_dispatch',lambda *a,**kw:pytest.fail('mutated packet must not dispatch'))
 with pytest.raises(pce.Changed):account_successor.run(c,'Q053-P011',**args,apply=True)


def test_exact_live_bindings_and_candidate_delta():
 import hashlib
 for name,digest in json.loads((HERE/'bindings.json').read_text()).items():
  assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
 delta=json.loads((PACK/'successor.json').read_text());candidate=(PACK/'account-candidate.tex').read_text()
 assert len(delta['changes'])==1 and delta['changes'][0]['finding']=='P1'
 change=delta['changes'][0];assert candidate.count(change['after'])==1
 assert pce._sha(candidate.replace(change['after'],change['before'],1))==delta['parent_candidate_sha256']
 assert (PACK/'account-candidate.tex').read_bytes()==(ROOT/'operator-log/2026-10-20-affinity-floating-bounds/Q053-P011/account-candidate.tex').read_bytes()


def test_preparation_retains_full_reserve_before_writes(tmp_path,monkeypatch):
 c,t,args=setup(tmp_path,monkeypatch);before=pce_recovery.hashes(t)
 monkeypatch.setattr(transport,'max_prompt_chars',lambda c:800000)
 monkeypatch.setattr(pce,'_dispatch',lambda *a,**kw:pytest.fail('no calls'))
 with pytest.raises(pce.Changed,match='plus reserve exceeds'):
  account_successor.run(c,'Q053-P011',**args)
 assert pce_recovery.hashes(t)==before
