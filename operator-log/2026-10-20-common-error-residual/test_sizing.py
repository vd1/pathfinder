"""Offline transport sizing only: real old reports are never successor judgements."""
import importlib.util,json,shutil
from pathlib import Path
from pathfinder import account_successor,editor_packet,pce
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder');PACK=ROOT/'operator-log/2026-10-20-common-error-residual'
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_real_profile_sizing(tmp_path,monkeypatch):
    assert Path(pce.__file__).resolve().is_relative_to(Path('/private/tmp/pathfinder-editor-9c139ff'))
    c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q024-P022','allocation-definitions-20261020','motivation-context-1')
    delta=json.loads((PACK/'Q024-P022/successor.json').read_text())
    for row in delta['evidence_projection']['include']:
        dst=t/row['path'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(helper.BASE/'threads/Q024-P022'/row['path'],dst)
    calls=script(monkeypatch,c)
    parent=t/'edited/account-amendments/allocation-definitions-20261020/revisions/motivation-context-1/review'
    # Scope captured from canonical successor assembly; only size-probe substitutions below.
    real_alias=pce.editor_alias_packet
    class Measured(Exception):pass
    def measure(head,shown):
        profile=dict(shown);replaced=[]
        for name in shown:
            if name.startswith(('claims/','reviews/')) or (name.startswith('revisions/history/') and name.endswith(('-claims.json','.md'))):
                source=parent/name
                assert source.is_file(),name
                profile[name]=source.read_text();replaced.append(name)
        alias,_=real_alias(head,profile);raw,meta=editor_packet.packet(head,profile,len(alias))
        assert editor_packet.decode(raw.split('Allowed input files:\n',1)[1])==profile
        stress=dict(profile)
        fact_names=[n for n in profile if n.startswith('reviews/') and n.endswith('fact-check.json')]
        for name in fact_names:
            fact=json.loads(stress[name]);fact['offline_sizing_padding']='x'*40000;stress[name]=pce._json(fact)
        stress_alias,_=real_alias(head,stress);stress_raw,_=editor_packet.packet(head,stress,len(stress_alias))
        assert editor_packet.decode(stress_raw.split('Allowed input files:\n',1)[1])==stress
        assert len(stress_raw)<1_000_000
        result={'purpose':'Offline sizing only; historical reports are NOT reviews of successor. No live dispatch.',
                'historical_claim_count':len(json.loads((parent/'claims/current.json').read_text())),
                'fact_claim_count':len(json.loads((parent/'reviews/current/fact-check.json').read_text())['claims']),
                'original_chars':len(head+pce._json(profile)),'json_alias_chars':len(alias),
                'raw_unique_chars':sum(len(s) for s in set(profile.values())),'raw_prompt_chars':len(raw),
                'stress_extra_unique_report_chars':40000,'stress_raw_prompt_chars':len(stress_raw),'cap':1000000,'headroom':1000000-len(raw),'files':len(profile),'replaced_profile_paths':replaced,
                'exact_expanded_file_hashes':{n:pce._sha(v) for n,v in profile.items()},
                'actual_successor_sources_preserved':all(profile[k]==v for k,v in shown.items() if k.startswith('sources/')),
                'four_stub_roles_only':len(calls)==4,'editor_dispatched':False}
        (PACK/'editor-sizing.json').write_text(json.dumps(result,indent=2)+'\n')
        print({k:v for k,v in result.items() if k not in ('exact_expanded_file_hashes','replaced_profile_paths')})
        raise Measured
    stub_dispatch=pce._dispatch
    def dispatch(c,pair,role,prompt,**kwargs):
        if role=='editor':
            head,body=prompt.split('Allowed input files:\n',1)
            measure(head+'Allowed input files:\n',json.loads(body))
        return stub_dispatch(c,pair,role,prompt,**kwargs)
    monkeypatch.setattr(pce,'_dispatch',dispatch)
    import pytest
    with pytest.raises(Measured):
        account_successor.run(c,'Q024-P022',identity='common-error-definition-20261020',packet=PACK/'Q024-P022',reason='OFFLINE sizing only; no scientific judgement',apply=True)
    assert len(calls)==4 and not any(x['role']=='editor' for x in calls)
