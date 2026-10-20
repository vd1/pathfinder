import copy,importlib.util,json
from pathlib import Path
from unittest.mock import patch
from pathfinder import config,library,pce
ROOT=Path('/Users/v/Code_2026/pathfinder');BASE=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2');PAIR='Q053-P011';ID='scalar-allowance-definition-20261020';REV=None
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
def measure(tmp_path,monkeypatch):
    with monkeypatch.context() as local:
        local.delenv('PATHFINDER_SOURCE_CACHE',raising=False)
        pool=library.cache(config.load(BASE)).resolve()
    c,t=helper.copied(tmp_path,monkeypatch,BASE,PAIR,ID,REV)
    # Preserve live configuration and cached prompt paths while replaying saved receipts only.
    c=config.load(c.root);monkeypatch.setattr(library,'cache',lambda c:pool)
    c._pce_workflow=t/'edited/account-amendments'/ID/'review'
    original=pce.editor_alias_packet
    def alias(head,shown):
        prompt,meta=original(head,shown)
        out={'head':head,'shown':shown,'original_chars':len(head+pce._json(shown)),'alias_chars':len(prompt),'raw_unique_chars':sum(len(x) for x in set(shown.values())),'files':len(shown),'unique_files':len(set(shown.values()))}
        Path('/private/tmp/scalar-editor-measure.json').write_text(json.dumps(out))
        raise RuntimeError('measured copied editor context')
    monkeypatch.setattr(pce,'editor_alias_packet',alias)
    monkeypatch.setattr(pce,'_dispatch',lambda *a,**k:(_ for _ in ()).throw(AssertionError('no dispatch allowed')))
    try:pce.run(c,PAIR)
    except RuntimeError as e:assert str(e)=='measured copied editor context'
    return json.loads(Path('/private/tmp/scalar-editor-measure.json').read_text())
def test_measure(tmp_path,monkeypatch):
    d=measure(tmp_path,monkeypatch);print({k:v for k,v in d.items() if k not in ('head','shown')})
