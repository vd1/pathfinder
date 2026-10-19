import json
import pytest
from pathfinder import account_release, paper, presentation, release, pce_recovery
from test_imported_account_release import imported
from test_presentation import _script, edited, check

BAD='Its scientific status remains DRAFT; editorial approval does not constitute a new scientific verdict.'
GOOD='The results remain subject to the stated assumptions and evidence limitations; editing provides no additional scientific validation.'
LIMIT='Supporting generated research material is not independent ground truth.'


def test_host_catches_model_clear_and_guarded_correction_preserves_limit(tmp_path,monkeypatch):
    c,ed,old=imported(tmp_path)
    before=pce_recovery.hashes(old)
    anchor='The proposed experiment remains untested.'
    calls=_script(monkeypatch,{'present/editor':[edited((anchor,anchor+' '+BAD+' '+LIMIT))],
        'present_check/checker':[check(),check()], 'present/corrector':[edited((BAD,GOOD))]})
    assert account_release.present(c,'Q1P1')=='CLEARED'
    view=account_release.view(c,'Q1P1')
    final=presentation.final(view,'Q1P1').read_text()
    assert GOOD in final and LIMIT in final and BAD not in final
    assert 'host-release-language' in (presentation.folder(view,'Q1P1')/'pass/release-language.json').read_text()
    assert len([x for x in calls if x.actor=='corrector'])==1
    assert account_release.release(c,'Q1P1',timestamp='20261019T200000Z')['status']=='RELEASED'
    assert before==pce_recovery.hashes(old)


def test_restart_archives_cleared_pass_invalidates_clearance_and_runs(tmp_path,monkeypatch):
    c,ed,old=imported(tmp_path)
    _script(monkeypatch,{'present/editor':[edited()], 'present_check/checker':[check()]})
    assert account_release.present(c,'Q1P1')=='CLEARED'
    view=account_release.view(c,'Q1P1');pd=paper.folder(view,'Q1P1')
    before=pce_recovery.hashes(presentation.folder(view,'Q1P1'))
    def interrupted(request):
        assert paper.status(view,'Q1P1')['status']=='ACCEPTED'
        assert paper.status(view,'Q1P1')['cleared_sha256'] is None
        raise RuntimeError('simulated interruption')
    _script(monkeypatch,{'present/editor':[interrupted]})
    with pytest.raises(RuntimeError,match='interruption'):account_release.present(c,'Q1P1',restart=True)
    archive=pd/'presentation-history/attempt-0001'
    assert all(pce_recovery.hashes(archive)[k]==v for k,v in before.items())
    with pytest.raises(SystemExit,match='not CLEARED'):account_release.release(c,'Q1P1')
    _script(monkeypatch,{'present/editor':[edited()], 'present_check/checker':[check()]})
    assert account_release.present(c,'Q1P1')=='CLEARED'


def test_leak_remains_blocking_when_models_keep_it(tmp_path,monkeypatch):
    c,ed,old=imported(tmp_path);c.raw['presentation_cycles']=0
    _script(monkeypatch,{'present/editor':[edited(('The proposed experiment remains untested.',BAD+' '+LIMIT))],
                         'present_check/checker':[check()]})
    assert account_release.present(c,'Q1P1')=='PAUSE-ON-PRESENT'
    with pytest.raises(SystemExit,match='not CLEARED'):account_release.release(c,'Q1P1')
    assert release.leak_check(c,'\\begin{document}'+BAD,BAD)


def test_account_instruction_is_internal_and_preserves_scientific_limits(tmp_path):
    c,ed,old=imported(tmp_path);view=account_release.view(c,'Q1P1',create=True)
    prompt=presentation._task(view,'Q1P1','present')
    assert 'Internal instruction only, never manuscript prose' in prompt
    assert 'Do not copy status labels' in prompt
    assert 'no additional scientific validation' in prompt
