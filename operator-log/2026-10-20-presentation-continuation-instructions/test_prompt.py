import importlib.util,json,hashlib
from pathlib import Path
from pathfinder import account_release,context,paper,presentation
ROOT=Path('/Users/v/Code_2026/pathfinder');PACK=ROOT/'operator-log/2026-10-20-presentation-continuation-instructions'
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
def test_retained_prompt_reconstruction(tmp_path,monkeypatch):
 c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q024-P022','common-error-definition-20261020')
 v=account_release.view(c,'Q024-P022');pd=paper.folder(v,'Q024-P022');d=presentation.folder(v,'Q024-P022')
 grant=json.loads((pd/'presentation-continuations/coefficient-summary-context-20261020/grant.json').read_text())
 v._presentation_context=json.loads((ROOT/'operator-log/2026-10-20-allocation-coefficient-context/context.json').read_text())
 found=json.loads((d/'pass/check.json').read_text())['findings']
 prior=json.loads((d/'pass/claims-5e8713c08408496a2ca4d970d0459de6551131a399fb21bd04815325585a672a.json').read_text())
 for asked,answer in zip(prior['asked'],prior['answers']):
  if answer['decision']=='presentation':
   item={k:asked[k] for k in ('where','issue','kind')};found.append({**item,**answer})
 sections=[]
 if getattr(v,'_bibliography_metadata',None):sections.append(context.Section('verified bibliography metadata correction (metadata only)',text=json.dumps(v._bibliography_metadata),keep=True))
 sections += [context.Section('accepted manuscript (reference only, to restore wording; do not return it)',text=(pd/'paper.tex').read_text()),context.Section('checker findings to resolve',text=json.dumps(found,indent=1),keep=True),context.Section('manuscript',text=(d/'pass/paper.tex').read_text(),keep=True),context.Section('references.bib',text=(d/'pass/references.bib').read_text(),keep=True),context.Section('your task',text=presentation._task(v,'Q024-P022','present-correct'),keep=True)]
 prompt=context.build(v,'present',sections,tools=False,record=False)
 print([(x.name,len(context._render(x,x.body()))) for x in sections],len(prompt))
 actual=(d/'correct-2-refused/input-sha256.txt').read_text().strip()
 assert hashlib.sha256(prompt.encode()).hexdigest()==actual
 assert grant['request']['reason'] not in prompt
 assert 'remove the sentence if it adds no necessary information' in prompt
 assert 'correction refused by the guard: deletes accepted text:' not in prompt
 (PACK/'prompt-diagnosis.json').write_text(json.dumps(dict(prompt_sha256=actual,chars=len(prompt),exact_recorded_hash_match=True,grant_reason_transmitted=False,prior_guard_refusal_transmitted=False,old_checker_removal_option_present=True),indent=2)+'\n')
