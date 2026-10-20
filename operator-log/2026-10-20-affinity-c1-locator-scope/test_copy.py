"""Actual paused account on the existing frozen engine; no scientific executions."""
import importlib.util,json,re,shutil
from pathlib import Path
import pytest
from pathfinder import account_present,account_release,presentation,paper,pce,pce_recovery
from test_presentation import _script,check,manuscript
PACK=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('helper',PACK.parent/'2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
PAIR='Q053-P011';IDENTITY='floating-bound-definition-20261020'

@pytest.mark.parametrize('damage',[None,'source','context','prior-output'])
def test_copy(tmp_path,monkeypatch,damage):
 assert Path(account_present.__file__).resolve().is_relative_to('/private/tmp/pathfinder-whole-body-438592b')
 c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,PAIR,IDENTITY)
 context=json.loads((PACK/'context.json').read_text())
 for e in context['contexts']:
  path=t/e['source'];path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(helper.BASE/'threads'/PAIR/e['source'],path)
 before=pce_recovery.hashes(t);v=account_release.view(c,PAIR);pd=paper.folder(v,PAIR);d=presentation.folder(v,PAIR)
 original=(d/'pass/paper.tex').read_text();accepted=(pd/'paper.tex').read_text();final=(PACK/'expected-correction.tex').read_text()
 reason=json.loads((PACK/'action.json').read_text())['prepare_argv'][-1]
 args=dict(identity='c1-locator-scope-1',context_path=PACK/'context.json',reason=reason)
 def correct(req):
  assert manuscript(req.prompt)==original
  assert accepted in req.prompt
  assert json.dumps(reason,ensure_ascii=False) in req.prompt
  assert 'prior_refusal' in req.prompt and 'Do not repeat the change identified in the prior' in req.prompt
  for e in context['contexts']:assert json.dumps(e['quote'],ensure_ascii=False) in req.prompt
  transformed=original
  for x in json.loads((PACK/'proposed-change.json').read_text()):
   assert transformed.count(x['before'])==1;transformed=transformed.replace(x['before'],x['after'],1)
  assert transformed==final
  scope=json.loads((PACK/'scope.json').read_text())
  previous=(d/'correct-2-refused/paper.tex').read_text()
  for text in scope['removed_only_from_refused']:
   assert previous.count(text)==1;previous=previous.replace(text,'',1)
  assert previous==final
  assert set(re.findall(r'\\texttt\{([^}]+)\}',final))-set(re.findall(r'\\texttt\{([^}]+)\}',original))<=set(scope['allowed_new_reference_strings'])
  assert 'v6' not in final
  assert re.findall(r'\\\[(.*?)\\\]',original,re.S)==re.findall(r'\\\[(.*?)\\\]',final,re.S)
  assert not presentation.guard(original,final,accepted,(pd/'references.bib').read_text())
  assert presentation.guard(original,final+r' Its frozen rule is in \texttt{v6-domain-frozen.txt} and \texttt{v6\_audit.py}.',accepted,'')
  for phrase in ['These counts are not probabilities','Those fits lack learned series offsets','Neither fit has become a validated affinity prediction','Repeated preparations are neither independent observations nor a probabilistic ensemble']:
   assert phrase in original and phrase in final
  return '===PAPER===\n'+final+'\n===REPORT===\n'+json.dumps(dict(changelog=['Define primary response set and aggregate RMSE; restore C1 supporting records without ledger-entry locators.'],title=None,findings=[],escalations=[]))
 calls=_script(monkeypatch,{'present/corrector':[correct],'present_check/checker':[check()]})
 if damage=='source':
  path=t/context['contexts'][0]['source'];path.write_text(path.read_text()+'changed')
 if damage=='context':
  cp=tmp_path/'context.json';context['contexts'][0]['quote']='invented target';cp.write_text(json.dumps(context));args['context_path']=cp
 if damage in ('source','context'):
  with pytest.raises(pce.Changed):account_present.apply(c,PAIR,**args)
  assert not calls;return
 assert 'no calls' in account_present.apply(c,PAIR,**args)
 if damage=='prior-output':
  path=d/'correct-2-refused/report.json';path.write_text(path.read_text()+' ')
  with pytest.raises(pce.Changed):account_present.apply(c,PAIR,**args,resume=True)
  assert not calls;return
 assert account_present.apply(c,PAIR,**args,resume=True)=='CLEARED'
 assert [(x.stage,x.actor)for x in calls]==[('present','corrector'),('present_check','checker')]
 assert (d/'correct-3/paper.tex').read_text()==final
 after=pce_recovery.hashes(t);changed=[n for n,h in before.items()if after.get(n)!=h]
 assert set(changed)<={str((d/'state.json').relative_to(t)),str((pd/'paper.json').relative_to(t)),str((pd/'presentation-continuation.json').relative_to(t))},changed
 acceptance=json.loads((pd/'acceptance.json').read_text());root=t/'edited/account-amendments'/IDENTITY
 for n,digest in acceptance['files_sha256'].items():assert pce_recovery.hashes(root)[n]==digest
 build=tmp_path/'build';build.mkdir();shutil.copyfile(d/'correct-3/paper.tex',build/'paper.tex');shutil.copyfile(pd/'references.bib',build/'references.bib')
 ok,log=paper.build(build);assert ok,log
 (PACK/'verification.json').write_text(pce._json(dict(runtime=str(Path(presentation.__file__).resolve()),calls=[x.stage+'/'+x.actor for x in calls],stub_clearance=True,real_build=True,unchanged_prior_files=len(before)-len(changed),changed=changed,accepted_custody_files=len(acceptance['files_sha256']),ordinary_guard=True,quotations=len(context['contexts']))))
