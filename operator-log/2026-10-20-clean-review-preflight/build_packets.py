"""Generate explicit deletion-only projections of retained review inputs; no scientific execution."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2/threads')
CASES={
 'affinity':('Q053-P011','preparation-spec-20261020','affinity-cycle-definitions-1'),
 'bundle':('Q053-P024','conditional-information-20261020','gaussian-noise-framing-1'),
 'allocation':('Q024-P022','allocation-domain-20261020','aggregate-validation-1')}
sha=lambda x:hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
# Literal removals were inspected in their full scientific context. Every omitted
# byte and its surviving complement are recorded below, including workflow tags.
REMOVE={
 'affinity':[
 ', incorporating its verifier #90',
 'Reviewer independently recomputed these counts. ',
 '(branch-3 V3-I1, branches/branch-3/ledger.jsonl #90) ',
 'Specialist review failed to start due to collaboration-tool context error; this addition has no independent reviewer sign-off.',
 'Verifier #27 ',
 ' or reviewer sign-off',
 'Independent implementation/quantum-scope review launch also failed with the same collaboration context error; no sign-off is claimed.',
 'The verifier #27 requests are completed for the enumerated domains: ',
 'The supplied Q8P1.tex still says those checks are open and restricts the predictive negative to primary sources; that is superseded by joint #31-34 and #39-41. ',
 'Vera requests: ', 'V1 answered by ', 'V2 answered by ', 'V3 answered by ', 'V4: ', 'V5 ',
 'Independent acceptance of V3/V5 clarifications: ',
 'Vera V3 ',
 'Current account after Vera requests: V1 is repaired by ',
 'V2 explicitly records ', 'V3 has ', 'V4 recovered ', 'V5 finds ',
 'The final LOOCV addition lacks independent reviewer sign-off: collaboration\nfailed to initialise a reviewer. ',
 ' after verifier joint #27',
 ' Specialist review launches\nfailed at tool-context initialisation, so no independent sign-off is claimed.',
 'The completed calculations answer verifier joint #27. ',
 'The supplied Q8P1.tex predates these results: its primary-only restriction\nand proposed next steps are now stale. The note can use joint #31-34 and\n#39-41 plus this independent cross-check when rewritten by its author.\n',
 ],
 'bundle':[
 'Current account for Vera after #40: ', 'V1-R1 is answered by ', 'V1-I1 is answered by ',
 'Current account after reading through #45: Vera R2 is answered by #34/#45; I3 by #38; I2 by #35/#43/#45, independently replayed by Ada #40. Ada R1 and I1 are independently checked in #44 and my thermal-register recheck. ',
 'Current account after reading through #51: existing replies address Vera R1 (#33/#46), R2 (#34/#45), I1 (#36-37/#44), I2 (#35/#40/#43/#45), and I3 (#38-39). ',
 '; formal dispositions remain Vera responsibility',
 'Ada current account after Vera revisions, extending #32 and superseding its unavailable-input list: ',
 'I3 now has ',
 'Vera requests now have explicit evidence. ',
 ', without presuming verifier acceptance',
 "Vera's ",
 ],
 'allocation':[
 'No partner entry or Vera request was received after #21.',
 'Vera V1/V2 corrections now explicitly include ', 'V3 attained ', 'V4 attained ', 'V5 bounded ',
 'Best current Emmy account after Vera repairs: ',
 ]}

def project(text,tag):
 spans=[]
 if tag=='bundle' and 'Ada current account after Vera revisions' in text:
  for m in re.finditer(r'\bR[134] ',text):spans.append((m.start(),m.end(),'review request label',m.group()))
 for literal in REMOVE[tag]:
  for m in re.finditer(re.escape(literal),text):spans.append((m.start(),m.end(),'prior review/editorial framing',literal))
 for m in re.finditer(r'\bV\d+-[RI]\d+(?:/[RI]\d+)*\b\s*',text):
  spans.append((m.start(),m.end(),'prior-review request identifier',m.group()))
 # Cover overlapping tag removals without changing any surviving byte.
 merged=[]
 for a,b,_,_ in sorted(spans):
  if merged and a<=merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
  else:merged.append([a,b])
 kept=[];pos=0
 for a,b in merged:
  if pos<a:kept.append([pos,a])
  pos=b
 if pos<len(text):kept.append([pos,len(text)])
 return ''.join(text[a:b] for a,b in kept),dict(original_sha256=sha(text),projected_sha256=sha(''.join(text[a:b] for a,b in kept)),kept_spans=kept,removed_spans=[dict(start=a,end=b,text=text[a:b],reason='prior-review or editorial framing only; scientific clauses retained') for a,b in merged])

def build(tag):
 pair,identity,revision=CASES[tag];thread=BASE/pair;root=thread/'edited/account-amendments'/identity/'revisions'/revision
 original=json.loads((root/'review/frozen-inputs.json').read_text());supp=original['sources/external/research-supplement.md'];snap=json.loads((root/'evidence-snapshots.json').read_text())
 files={};manifest={};inventory={};rows=0
 for m in re.finditer(r'## ([^\n]+)\n(.*?)(?=\n## |\Z)',supp,re.S):
  if not m[1].endswith('ledger.jsonl'):continue
  records=[];audits=[]
  for line in m[2].splitlines():
   match=re.fullmatch(r'#(\d+) \[([^,]+), ([^]]+)\] \[([^]]+)\] (.*)',line)
   if not match:continue
   text,audit=project(match[5],tag);records.append(dict(seq=int(match[1]),actor=match[2],kind=match[3],standing=match[4],text=text));audits.append(dict(seq=int(match[1]),**audit));rows+=1
  files[m[1]]='\n'.join(json.dumps(r,ensure_ascii=False) for r in records)+'\n';manifest[m[1]]=dict(kind='ledger',entries=audits)
 embedded=json.loads(supp.split('## Approved retained scientific files',1)[1])
 for name,text in embedded.items():
  files[name],audit=project(text,tag);manifest[name]=dict(kind='scientific file',**audit)
 for key,text in original.items():
  if not key.startswith('sources/external/'):continue
  if key.endswith('/research-supplement.md'):
   inventory[key]=dict(disposition='all ledger rows/standing and embedded files retained with exact audited framing removals',sha256=sha(text));continue
  if key in ('sources/external/P.txt','sources/external/Q.txt'):
   inventory[key]=dict(disposition='unchanged external paper',sha256=sha(text));continue
  matches=[n for n,t in snap.items() if t==text];name=matches[0] if len(matches)==1 else key
  clean,audit=project(text,tag)
  if name in files:assert files[name]==clean
  files[name]=clean;manifest[name]=dict(kind='original external scientific file',**audit)
  inventory[key]=dict(disposition='embedded exact scientific payload or explicitly audited framing projection',path=name,sha256=sha(text))
 if tag=='allocation':
  delta=json.loads((HERE.parent/'2026-10-20-allocation-definitions/Q024-P022/successor.json').read_text())
  for row in delta['evidence_projection']['include']:
   text=(thread/row['path']).read_bytes().decode();assert sha(text)==row['sha256'];files[row['path']]=text
   manifest[row['path']]=dict(kind='approved successor addition',original_sha256=sha(text),projected_sha256=sha(text),kept_spans=[[0,len(text)]],removed_spans=[])
 data={'files':files,'coverage_limit':'Retained scientific record, not independent literature. All original external payloads and ledger standing accounted for; exact projection manifest records only prior-review/editorial framing removals. No universal branch adoption inferred.'}
 out={'external':{'P.txt':original['sources/external/P.txt'],'Q.txt':original['sources/external/Q.txt'],'research-supplement.md':json.dumps(data,ensure_ascii=False,indent=1)+'\n'}}
 dest=HERE/tag;dest.mkdir(exist_ok=True);(dest/'inputs.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 (dest/'projection-manifest.json').write_text(json.dumps(dict(source_frozen_sha256=sha((root/'review/frozen-inputs.json').read_bytes()),source_supplement_sha256=sha(supp),ledger_rows=rows,files=manifest,external_inventory=inventory),ensure_ascii=False,indent=2)+'\n')
 (dest/'bindings.json').write_text(json.dumps({str(p):sha(p.read_bytes()) for p in [root/'candidate.tex',root/'request.json',root/'review/frozen-inputs.json',root/'review/result.json']},indent=2)+'\n')
 print(tag,'rows',rows,'files',len(files),'removed spans',sum(len(a.get('removed_spans',[])) for v in manifest.values() for a in v.get('entries',[v])))
 for name,text in files.items():
  if re.search(r'\bVera\b|\bverifier\b(?!-response)|Q\d+P\d+\.tex|reviewer sign-off',text,re.I):
   for line in text.splitlines():
    if re.search(r'\bVera\b|\bverifier\b(?!-response)|Q\d+P\d+\.tex|reviewer sign-off',line,re.I):print('CHECK',name,line[:250])
if __name__=='__main__':
 for tag in CASES:build(tag)
