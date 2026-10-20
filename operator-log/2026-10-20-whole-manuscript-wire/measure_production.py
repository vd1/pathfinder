"""Read-only sizing; failed reports are fixtures, never new scientific judgments."""
import json,time,random,string
from pathlib import Path
from pathfinder import pce,config,raw_literals,resources
from pathfinder import whole_bodies as prototype
import grouped
ROOT=Path('/Users/v/Code_2026/pathfinder');HERE=Path(__file__).resolve().parent
base=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2');t=base/'threads/Q053-P011'
r=t/'edited/account-amendments/floating-bound-definition-20261020/review';old=t/'edited/account-amendments/feature-record-specifications-20261020/review';c=config.load(base)
frozen=json.loads((r/'frozen-inputs.json').read_text());grant=json.loads((r/'grant.json').read_text());files=dict(frozen)
for folder in ['drafts','claims','reviews','revisions']:
 for f in sorted((r/folder).rglob('*')):
  if f.is_file():files[str(f.relative_to(r))]=f.read_bytes().decode()
# No critic ran. The last genuine accepted critic is a size fixture ONLY.
for k in ['reviews/current/critic-computational-chemist.md','reviews/history/pass-01-computational-chemist-critic.md']:
 files[k]=(old/k).read_bytes().decode()
head,editor=pce.role_context(c,'editor',['reviews/editor-feedback.md'],files,grant,FEEDBACK='reviews/editor-feedback.md')
def size(shown,head,role):
 start=time.perf_counter();payload,h,stats=prototype.encode(shown,role)
 assert prototype.decode(payload,{n:prototype.sha(v) for n,v in shown.items()},role)==shown
 # Exact labelled prototype payload; no estimated framing savings.
 head=head.replace(pce.TRANSPORT,pce.TRANSPORT.replace("The JSON mapping","The labelled whole-body packet"),1)
 label_chars=0
 return dict(chars=len(prototype.INSTRUCTION+head+payload)+label_chars,payload_sha256=prototype.sha(payload),inline_label_chars=label_chars,seconds=time.perf_counter()-start,stats=stats,expanded_sha256={n:prototype.sha(v)for n,v in shown.items()})
grouped.PROTECT_REPORTS=True;grouped.ONLY_SUPPLEMENT=True
results=[]
for chunk,anchor,minimum in [(8192,32,192)]:
 grouped.CHUNK=chunk;grouped.ANCHOR=anchor;grouped.MIN_COPY=minimum
 row={'chunk':chunk,'anchor':anchor,'minimum_copy':minimum,'profile':'whole manuscripts/claims/replacements/reports with direct identity groups','prep':size(frozen,'','preparation'),'editor':size(editor,head,'editor')}
 row['prep_plus_reserve']=row['prep']['chars']+100000
 row['stress']=[]
 for n in [8192,32768]:
  rng=random.Random(73);noise=''.join(rng.choices(string.ascii_letters+string.digits,k=n));m=dict(editor)
  fact=json.loads(m['reviews/current/fact-check.json']);fact['offline_capacity_stress_note']=noise
  for k in list(m):
   if k.startswith('reviews/') and k.endswith('fact-check.json'):m[k]=pce._json(fact)
   if k.startswith('revisions/') and k.endswith('evidence-diff.json'):
    obj=json.loads(m[k]);obj['fact_check']=fact;m[k]=pce._json(obj)
  measured=size(m,head,'editor');measured['extra_distinct_fact_chars']=n;row['stress'].append(measured)
 results.append(row)
(HERE/'production-measurement.json').write_text(json.dumps(results,indent=2)+'\n')
for x in results:print(x['chunk'],x['anchor'],x['minimum_copy'],x['prep_plus_reserve'],x['editor']['chars'],[s['chars']for s in x['stress']],x['editor']['stats'])

roles={}
for role,allowed,values in [
 ('author',[pce.CLAIMS],dict(DRAFT=pce.DRAFT,CLAIMS_SCHEMA=pce._json(pce.CLAIMS_SCHEMA).strip())),
 ('archivist',['revisions/history/2026-10-20-pass-01.md'],dict(SNAPSHOT='revisions/history/2026-10-20-pass-01-draft.tex',SHA256=pce._sha(files[pce.DRAFT]),NOTE='revisions/history/2026-10-20-pass-01.md')),
 ('fact-checker',['reviews/history/pass-01-fact-check.json','reviews/current/fact-check.json'],dict(HISTORY='reviews/history/pass-01-fact-check.json',CURRENT='reviews/current/fact-check.json',FACT_SCHEMA=pce._json(pce.FACT_SCHEMA).strip())),
 ('critic',['reviews/history/pass-01-computational-chemist-critic.md','reviews/current/critic-computational-chemist.md'],dict(HISTORY='reviews/history/pass-01-computational-chemist-critic.md',CURRENT='reviews/current/critic-computational-chemist.md',PROFILE='computational-chemist',REMIT=grant['settings']['critic']['remit']))]:
 h,m=pce.role_context(c,role,allowed,frozen if role=='author' else files,grant,**values)
 if role in ('author','archivist','fact-checker'):
  vis=json.loads((r/f'visibility/pass-01-{role}.json').read_text())
  m={n:m[n] for n in vis['files_sha256']}
  assert {n:pce._sha(v) for n,v in m.items()}==vis['files_sha256']
 roles[role]=size(m,h,role)
roles['editor']=results[0]['editor']
reserve=max(results[0]['prep']['chars'],roles['author']['chars'])+100000
assert reserve<=1000000 and results[0]['stress'][0]['chars']<=1000000
(HERE/'all-role-measurement.json').write_text(json.dumps(dict(roles=roles,reserved_prompt_chars=reserve,host_only_continuation_metadata=True,model_continuation_instruction_chars=0,critic_fixture='Prior accepted critic used for sizing only; no fresh critic exists',stress=results[0]['stress']),indent=2)+'\n')
print('ROLES', {k:v['chars']for k,v in roles.items()},'RESERVE',reserve)
