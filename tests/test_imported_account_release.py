"""Imported acceptance is validated in place, never converted into a native PCE run."""
import json
import pytest
from pathfinder import account_release, edit, paper, pce, presentation, research
from pathfinder.import_eva2 import _sha
from stubcampaign import make


def imported(tmp_path):
    c = make(tmp_path, release={'disclosure': 'disclosure.tex'})
    research.run_thread(c, 'Q1P1')
    (c.root / 'disclosure.tex').write_text('Prepared with Pathfinder.')
    ed = c.thread_dir('Q1P1') / 'edited'; root = ed / 'eva2-pce'; root.mkdir(parents=True)
    body = '\\section{A bounded account}\nThe proposed experiment remains untested.\n'
    wrapper = '\\documentclass{article}\n\\usepackage{pathfinder-readable}\n\\date{}\n\\begin{document}\n'+body+'\\end{document}\n'
    for file in (ed / 'note.tex', root / 'account.tex'):
        file.write_text(body)
    for file in (ed / 'note.pdf', root / 'account.pdf'):
        file.write_bytes(b'preserved historical pdf')
    (root / 'account.build.tex').write_text(wrapper)
    record = {'source': 'reports/pce-01', 'editorial_status': 'accepted', 'pce_result': 'accepted',
              'kept_as': 'edited/eva2-pce', 'note_sha256': _sha(ed/'note.tex'), 'pdf_sha256': _sha(ed/'note.pdf')}
    (c.root / 'import.json').write_text(json.dumps({'edit':record}))
    (root / 'delivery.json').write_text(json.dumps({'editorial_status':'accepted','pce_result':{'status':'accepted'}}))
    (root / 'account.render.json').write_text(json.dumps({'passed':True,'source_sha256':record['note_sha256'],
        'document_sha256':_sha(root/'account.build.tex'),'pdf_sha256':record['pdf_sha256']}))
    edit._set(c,'Q1P1',status='done', imported_from='eva2 PCE',source='reports/pce-01',editorial_status='accepted')
    return c, ed, root


def test_imported_account_reaches_dated_release_without_native_acceptance(tmp_path, monkeypatch):
    from test_presentation import _script, edited, check
    c, ed, old = imported(tmp_path)
    old_files = {p:p.read_bytes() for p in ed.rglob('*') if p.is_file()}
    scientific = (c.thread_dir('Q1P1')/'status.json').read_bytes()
    monkeypatch.setattr(pce,'run',lambda *a,**k:pytest.fail('PCE must not run again'))
    calls = _script(monkeypatch, {'present/editor':[edited()], 'present_check/checker':[check()]})
    assert account_release.present(c,'Q1P1')=='CLEARED'
    out = account_release.release(c,'Q1P1',timestamp='20261019T160000Z')
    assert out['status']=='RELEASED'
    assert {r.stage for r in calls}=={'present','present_check'}
    assert all(p.read_bytes()==data for p,data in old_files.items())
    assert scientific==(c.thread_dir('Q1P1')/'status.json').read_bytes()
    assert pce.result(c,'Q1P1')['status']=='none'
    assert 'accepted_note' not in edit.status(c,'Q1P1')
    assert paper.status(c,'Q1P1')['status']=='none'
    v=account_release.view(c,'Q1P1')
    assert (paper.folder(v,'Q1P1')/'paper.tex').read_bytes()==(old/'account.build.tex').read_bytes()
    assert json.loads((paper.folder(v,'Q1P1')/'acceptance.json').read_text())['kind'].startswith('imported EVA2')


@pytest.mark.parametrize('change', ['body','wrapper','delivery','import','pdf','bib'])
def test_inconsistent_import_blocks_before_publication(tmp_path, change):
    c,ed,root=imported(tmp_path)
    if change=='body': (ed/'note.tex').write_text('changed body')
    if change=='wrapper': (root/'account.build.tex').write_text('changed wrapper')
    if change=='pdf': (ed/'note.pdf').write_bytes(b'changed PDF')
    if change=='delivery': (root/'delivery.json').write_text('{"editorial_status":"review_required"}')
    if change=='import': c.path('import.json').write_text('{"edit":{}}')
    if change=='bib':
        p=root/'account.build.tex'; p.write_text(p.read_text().replace('\\end{document}','\\cite{missing}\\end{document}'))
        r=root/'account.render.json'; data=json.loads(r.read_text()); data['document_sha256']=_sha(p);r.write_text(json.dumps(data))
    with pytest.raises(pce.Changed): account_release.view(c,'Q1P1',create=True)
    assert not (ed/'publication').exists()


def test_pairless_reconcile_resumes_prepared_grants_sequentially(tmp_path, monkeypatch):
    from pathfinder import cli, config, pce_recovery
    from test_pce import ready
    import shutil
    c=ready(tmp_path)
    shutil.copytree(c.thread_dir('Q1P1'),c.thread_dir('Q2P2'))
    c.path('shortlist.json').write_text(json.dumps({'pairs':[{'pair_id':'Q1P1'},{'pair_id':'Q2P2'}]}))
    for pair in ('Q1P1','Q2P2'): pce_recovery.grant(c,pair,'prepared',1,1,'finish review')
    monkeypatch.setattr(edit,'_install',lambda *a:None)
    cli.main(['--root',str(c.root),'reconcile','--apply'])
    assert all(pce.result(c,pair)['status']=='accepted' for pair in ('Q1P1','Q2P2'))
    assert all(len(pce.dispatches(c,pair))==5 for pair in ('Q1P1','Q2P2'))
