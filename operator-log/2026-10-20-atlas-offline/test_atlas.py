"""Private-copy Atlas integration test. Never run against a live campaign root."""
import hashlib,json,shutil
from collections import Counter
from pathlib import Path
from pathfinder import config,research,stub,transport,resources,collection,budget_group
ATLAS=Path('/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-1')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def test_actual_atlas_iterate_draft(tmp_path,monkeypatch):
    source=ATLAS/'operator/integration-check'
    roots=[(tmp_path/f'child-{i}').resolve() for i in range(1,7)]
    group=json.loads((source/'budget-group.json').read_text());group['campaigns']=list(map(str,roots))
    manifest=tmp_path/'budget-group.json';manifest.write_text(json.dumps(group))
    inputs_before={p:sha(p) for p in source.rglob('*') if p.is_file()}
    for i,root in enumerate(roots,1):
        root.mkdir()
        src=source/'campaigns'/f'child-{i}'
        for name in ('Q.jsonl','P.jsonl','shortlist.json'):shutil.copy(src/name,root/name)
        raw=json.loads((src/'campaign.json').read_text());raw['backend']='stub'
        for route in raw.get('routes',{}).values():route['backend']='stub'
        raw['budget_group']={'manifest':str(manifest),'sha256':sha(manifest)}
        (root/'campaign.json').write_text(json.dumps(raw))
        shutil.copytree(ATLAS/'prompts',root/'prompts')
    assert Path(config.__file__).resolve().is_relative_to(Path('/private/tmp/pathfinder-restricted-bbafa93'))
    c=config.load(roots[0]);pair=json.loads((roots[0]/'shortlist.json').read_text())['pairs'][0]['pair_id']
    sealed=collection.load(c);source_before={Path(f['path']):sha(Path(f['path'])) for row in sealed['sources'] for f in row['files']}
    calls=[];verdicts=iter(['ITERATE','DRAFT']);real=stub.reply
    def reply(campaign,request):
        assert campaign.backend=='stub'
        calls.append({'stage':request.stage,'actor':request.actor,'prompt':request.prompt})
        if request.stage=='verify':return json.dumps({'decision':next(verdicts),'reason':'offline contract fixture','action':'check the retained boundary'})
        return real(campaign,request)
    monkeypatch.setattr(stub,'reply',reply)
    # Native admission, routing, aggregate budget, receipts and stage transitions remain active.
    assert research.run_thread(c,pair)=='DRAFT'
    counts=Counter(r['stage'] for r in calls)
    assert counts=={'peer':2,'consolidate':2,'verify':2}
    for role in ('peer','consolidate','verify'):
        for call in (x for x in calls if x['stage']==role):
            appendix=ATLAS/'prompts'/f'{role}.append.md'
            if appendix.exists():assert appendix.read_text().strip() in call['prompt']
            assert '{{' not in call['prompt']
    receipts=transport.receipts(c)
    assert len(receipts)==6 and all(r['backend']=='stub' and r['cost']==0 for r in receipts)
    _,members,cap=budget_group.load(c);assert members==roots and budget_group.refusal(members,cap) is None
    assert all(sha(p)==h for p,h in inputs_before.items()) and all(sha(p)==h for p,h in source_before.items())
    assert not list(c.path('active-calls').glob('*.json'))
    out=tmp_path/'proof';out.mkdir()
    (out/'effective-prompts.json').write_text(json.dumps(calls,indent=2))
    (out/'verification.json').write_text(json.dumps({'backend':'stub','live_calls':0,'stages':counts,'overlay_digests':resources.prompt_digests(c),'receipts':receipts,'fixture_inputs_unchanged':True,'source_files_unchanged':True,'budget_members':list(map(str,members))},indent=2))
    print('Atlas native ITERATE -> DRAFT, six stub receipts, original overlays/collection and group guards; proof',out)
