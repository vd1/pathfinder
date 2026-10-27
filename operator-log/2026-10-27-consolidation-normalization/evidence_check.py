"""Read-only audit of retained Atlas replies; never changes historical records."""
from pathlib import Path
import hashlib,json,re
from pathfinder.thread import normalize_consolidation
root=Path('/Users/v/Code_2026/qap-atlas/pilots')
summary={};bindings={};normalized=[]
for number in [6,8,9]:
    counts=dict(records=0,preambles=0,normalizable=0,unchanged=0,invalid=0)
    for p in sorted((root/f'atlas-pilot-{number}').glob('runs/pair-*/threads/Q001-P002/consolidation/*.json')):
        original=p.read_bytes();bindings[str(p)]=hashlib.sha256(original).hexdigest()
        text=json.loads(original)['text'];out=normalize_consolidation(text);counts['records']+=1
        start=re.search(r'(?m)^\\documentclass\b',text)
        if start and start.start():
            counts['preambles']+=1
            if out is not None:
                counts['normalizable']+=1
                end=text.rfind(r'\end{document}')+len(r'\end{document}')
                assert out==text[start.start():end]+'\n'
                normalized.append({'path':str(p),'raw_sha256':hashlib.sha256(text.encode()).hexdigest(),
                                   'normalized_sha256':hashlib.sha256(out.encode()).hexdigest()})
        if out==text:counts['unchanged']+=1
        if out is None:counts['invalid']+=1
    summary[str(number)]=counts
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in bindings.items())
report=dict(summary=summary,bindings=bindings,normalized_on_copy=normalized,live_writes=0,model_calls=0)
Path(__file__).with_name('evidence-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(summary,indent=2))
