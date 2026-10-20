import importlib.util,json
from pathlib import Path
from pathfinder import account_revision,account_review,pce,pce_recovery
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder');PACK=ROOT/'operator-log/2026-10-20-selector-model-decision'
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_latest_clean_grant_child(tmp_path,monkeypatch):
    assert Path(account_revision.__file__).resolve().is_relative_to(Path('/private/tmp/pathfinder-editor-9c139ff'))
    c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q010-P030','selector-definitions-20261020')
    parent=t/'edited/account-amendments/selector-definitions-20261020/revisions/reference-decision-1'
    previous=account_review.workflow(parent);assert previous.name=='review'
    files=json.loads((previous/'frozen-inputs.json').read_text());assert len(json.loads(files[pce.SUPPLEMENT])['files'])==11
    before=pce_recovery.hashes(t/'edited');science=(t/'status.json').read_bytes();calls=script(monkeypatch,c)
    args=dict(identity='selector-definitions-20261020',revision='model-decision-1',packet=PACK/'Q010-P030',reason='Private copied latest-clean-grant child')
    assert 'no calls' in account_revision.run(c,'Q010-P030',**args)
    root=parent.parent/'model-decision-1';new=json.loads((root/'review/frozen-inputs.json').read_text())
    assert {k:v for k,v in files.items() if k.startswith('sources/external/')}=={k:v for k,v in new.items() if k.startswith('sources/external/')}
    assert 'accepted;' in account_revision.run(c,'Q010-P030',**args,apply=True);assert len(calls)==5
    assert (root/'build/paper.pdf').exists() and (t/'status.json').read_bytes()==science
    after=pce_recovery.hashes(t/'edited');assert all(after[n]==h for n,h in before.items() if n!='account-amendment.json')
    print('5 stub roles + real build; eleven clean files exact; preserved',len(before),'previous edited files')



def test_scope_preserves_numbers_and_limits():
    import hashlib,re
    packet=PACK/'Q010-P030';delta=json.loads((packet/'revision.json').read_text());candidate=(packet/'account-candidate.tex').read_text();old=candidate
    for d in reversed(delta['changes']):assert old.count(d['after'])==1;old=old.replace(d['after'],d['before'])
    assert hashlib.sha256(old.encode()).hexdigest()==delta['parent_candidate_sha256'] and len(delta['changes'])==2
    from collections import Counter
    numbers=lambda s:Counter(re.findall(r'(?<![A-Za-z])\d+(?:\.\d+)?',s))
    assert not (numbers(old)-numbers(candidate))
    for phrase in ('not embedded static/induction errors or accuracy certificates','no mean polarisability at that level is supplied','charge spill-out','not outstanding proposed calculations','without selecting a new accuracy threshold','not the untested response-tailored alternative','rather than identify determinants by unchanged bitstrings','not an imposed MP2 finite-difference prescription','A mean polarisability does not establish tensor ordering'):
        assert phrase in candidate
    context=json.loads((PACK/'retained-context.json').read_text());assert len(context['embedded_sha256'])==11
    assert all(e['standing']=='current; not cited by the joint ledger' for e in context['entries']['branches/branch-2/ledger.jsonl'])
    assert len(json.loads((packet/'changes.json').read_text())['changes'])==20

    parent=json.loads((helper.BASE/'threads/Q010-P030/edited/account-amendments/selector-definitions-20261020/revisions/reference-decision-1/request.json').read_text())['changes']['changes']
    records=json.loads((packet/'changes.json').read_text())['changes']
    assert records[:18]==parent
    # Reorganisation is a permutation of exact sentences/words; no decision or limitation disappears.
    from collections import Counter
    move=delta['changes'][1]
    stripped=move['after']
    for title in ('Completed baseline and diagnostics','Additional matched embedded comparison','Conditional selector decision'):
        stripped=stripped.replace('\\subsection{'+title+'}','')
    assert Counter(stripped.split())==Counter(move['before'].split())
    for phrase in ('zero-based active indices 6--11','inactive indices 0--5','External virtual orbitals, indices 12 onward','without field-specific RHF orbital optimisation'):
        assert phrase in candidate
