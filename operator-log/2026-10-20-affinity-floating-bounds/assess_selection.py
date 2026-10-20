from pathlib import Path
from types import SimpleNamespace
import json,hashlib
from pathfinder import pce,config,resources,library,account_register,editor_packet
root=Path('/Users/v/Code_2026/pathfinder'); out=root/'operator-log/2026-10-20-affinity-floating-bounds'
base=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2');t=base/'threads/Q053-P011';review=t/'edited/account-amendments/feature-record-specifications-20261020/review';pack=out/'Q053-P011'
c=config.load(base);delta=json.loads((pack/'successor.json').read_text()); candidate=(pack/'account-candidate.tex').read_text(); originals=json.loads((review/'frozen-inputs.json').read_text());actual=json.loads((review/'visibility/pass-01-editor.json').read_text());history=json.loads((review/'replacement-history.json').read_text())
contract=resources.prompt(c,'pce-editor',FEEDBACK='reviews/editor-feedback.md');head=contract.rstrip()+pce.TRANSPORT+'Permitted outputs: '+json.dumps(['reviews/editor-feedback.md'])+'\nAllowed input files:\n';head=library.request_rule(c,SimpleNamespace(prompt=head,tools=False,reads=False))+head
rows=delta['evidence_projection']['include'];script=(t/rows[0]['path']).read_bytes(); result=(t/rows[1]['path']).read_bytes()
# Retain header, complete model/input/graph/solver and cycle definitions. Omit only import/AST-loader block and terminal output statements.
start=script.index(b'import sys,');end=script.index(b'W, T, PARAMS, QUARTET')
kept=[(0,start),(end,len(script))]
# Explicitly retain output lines as well: no further selection or result omission.
selected=b''.join(script[a:b] for a,b in kept).decode()
manifest={'source':rows[0]['path'],'sha256':hashlib.sha256(script).hexdigest(),'kept':[{'start':a,'end':b,'sha256':hashlib.sha256(script[a:b]).hexdigest()} for a,b in kept],'omitted':[{'start':start,'end':end,'sha256':hashlib.sha256(script[start:end]).hexdigest(),'text':script[start:end].decode()}]}
metrics=[]
for mode in ['zero-new-evidence-lower-bound','full-result-only-lower-bound','full-separate','selected-separate']:
 files=dict(originals);old=files[pce.BASELINE]
 cand=candidate if mode!='selected-separate' else candidate.replace('The complete retained runner','The retained model, solver and cycle-definition spans from the runner')
 changes=json.loads(json.dumps(delta['changes']));changes[0]['after']=changes[0]['after'].replace('The complete retained runner','The retained model, solver and cycle-definition spans from the runner') if mode=='selected-separate' else changes[0]['after']
 files[pce.BASELINE]=cand;files['sources/internal/original.tex']=old;files['sources/internal/changes.json']=pce._json(dict(baseline_sha256=pce._sha(old),candidate_sha256=pce._sha(cand),changes=changes))
 for i,r in enumerate(rows):
  if mode=='zero-new-evidence-lower-bound' or (mode=='full-result-only-lower-bound' and i==0):continue
  body=(script if i==0 else result).decode() if mode in ['full-separate','full-result-only-lower-bound'] or i==1 else selected
  coverage='Complete raw file, no omissions.' if mode in ['full-separate','full-result-only-lower-bound'] or i==1 else f'Exact byte spans {kept}. Omitted bytes {start}:{end}: imports, argument parsing and AST loader only. Imported definitions/constants remain dependency-bound by endpoint_big_sha256 in the complete result. This is not a standalone executable or independent reproduction.'
  files[f'sources/external/amendment-retained-{i}.txt']=f'Retained research record: {r["path"]}\nRaw SHA-256: {r["sha256"]}\n{coverage}\n\n'+body
 assert all(files[k]==v for k,v in originals.items() if k.startswith('sources/external/'))
 prep=len(pce._json(files));reg=account_register.build(history['baseline'],history['changes']+changes,cand);files['sources/internal/changes.json']=pce._json({'changes':[{'finding':r['finding'],'after':r['claim']} for r in reg['records'] if r['claim'].strip()]})
 shown={}
 for name in actual['files_sha256']:
  if name in files:shown[name]=files[name]
  elif name.endswith('.tex'):shown[name]=cand
  else:shown[name]=(review/name).read_bytes().decode()
 shown.update({k:v for k,v in files.items() if k.startswith('sources/external/amendment-retained-')})
 def size(mapping):
  alias,_=pce.editor_alias_packet(head,mapping);raw,_=editor_packet.packet(head,mapping,len(alias));span,_=editor_packet.span_packet(head,mapping,len(alias),len(raw));assert editor_packet.decode_spans(span.split('Allowed input files:\n',1)[1])==mapping
  return len(span)
 n=size(shown);stress=[]
 for extra in [2048,8192]:
  # Fresh unique literal note appended identically to current and historical fact reports; preserved exact originals as prefixes.
  import random,string
  rng=random.Random(73);noise=''.join(rng.choices(string.ascii_letters+string.digits,k=extra))
  stressed=dict(shown)
  for key in list(stressed):
   if key.startswith('reviews/') and key.endswith('fact-check.json'):stressed[key]+='\n'+noise
  stress.append({'additional_note_chars':extra,'editor_chars':size(stressed)})
 metrics.append({'mode':mode,'prep_chars':prep,'reserve':100000,'prep_total':prep+100000,'actual_editor_chars':n,'headroom':1000000-n,'stress':stress,'old_external_identical':True,'paths':len(shown)})
(out/'selection-capacity-lower-bounds.json').write_text(json.dumps({'status':'OFFLINE ASSESSMENT ONLY: no canonical selected route or grant implemented','metrics':metrics,'script_partition':manifest,'result':'Complete raw result retained, all fields/all four ligand optimisation rows and cycle; no result omissions'},indent=2)+'\n')
print(json.dumps(metrics,indent=2))
