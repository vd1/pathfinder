from pathlib import Path
import importlib.util,json,time
from pathfinder import editor_blocks as b, editor_packet as ep
p=json.loads(Path('/private/tmp/affinity-complete-profile.json').read_text());source=Path(b.__file__).read_text();rows=[]
for roots in [('drafts/current.tex','reviews/current/fact-check.json'),('drafts/current.tex','claims/current.json','reviews/current/fact-check.json'),('drafts/current.tex','reviews/current/critic-computational-chemist.md','reviews/current/fact-check.json')]:
 for minimum in (256,192):
  s=source.replace("name != 'drafts/current.tex'",f'name not in {roots!r}').replace("'sources/internal/baseline.tex')","'sources/internal/baseline.tex', 'sources/internal/changes.json')").replace('MIN_COPY = 256',f'MIN_COPY = {minimum}')
  path=Path(f'/private/tmp/engine_blocks_probe_{len(rows)}.py');path.write_text(s);spec=importlib.util.spec_from_file_location('pathfinder._blocks_probe',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);b.encode=mod.encode;start=time.perf_counter();out,meta=ep.span_packet(p['head'],p['shown'],1117493,1045870);assert ep.decode_spans(out.split('Allowed input files:\n',1)[1])==p['shown'];rows.append({'raw_roots':roots,'min_copy':minimum,'chars':len(out),'headroom':1000000-len(out),'seconds':time.perf_counter()-start})
print(rows);Path('/Users/v/Code_2026/pathfinder/operator-log/2026-10-20-affinity-floating-bounds/raw-root-experiment.json').write_text(json.dumps(rows,indent=2)+'\n')
