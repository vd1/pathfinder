import json
import pytest
from pathfinder import account_amend, account_release, paper, pce, pce_recovery, presentation, edit
from test_imported_account_release import imported
from test_pce import script


def packet(tmp_path):
    c, ed, old = imported(tmp_path)
    v = account_release.view(c, 'Q1P1', create=True)
    d = presentation.folder(v, 'Q1P1'); d.mkdir()
    (d/'state.json').write_text(json.dumps({'state':'RETURNED'}))
    (d/'amend-findings.json').write_text(json.dumps({'findings':[{'id':'P1','issue':'Define scope.'}]}))
    baseline = (old/'account.build.tex').read_text()
    before = 'The proposed experiment remains untested.'
    after = before + ' The empty minimum is infinity.'
    candidate = baseline.replace(before, after)
    evidence = c.thread_dir('Q1P1')/'branches/branch-1/derivation.txt'
    evidence.parent.mkdir(parents=True, exist_ok=True); evidence.write_text('An empty minimum is infinity.')
    pk = tmp_path/'packet'; pk.mkdir()
    (pk/'account-candidate.tex').write_text(candidate)
    (pk/'changes.json').write_text(json.dumps({'baseline_sha256':pce._sha(baseline),
        'candidate_sha256':pce._sha(candidate), 'changes':[{'finding':'P1','before':before,'after':after}]}))
    (pk/'evidence.json').write_text(json.dumps({'source_files':[{'path':str(evidence.relative_to(c.root)),
        'sha256':pce._sha(evidence.read_text())}]}))
    args = dict(identity='definitions', packet=pk, evidence_root=c.root, reason='Owner authorises definition correction')
    return c, ed, candidate, args


def test_fixed_candidate_independent_acceptance_fresh_tail_and_idempotence(tmp_path, monkeypatch):
    from test_presentation import _script, edited, check
    c, ed, candidate, args = packet(tmp_path)
    before = pce_recovery.hashes(ed)
    calls = script(monkeypatch, c)
    assert 'no calls' in account_amend.apply(c, 'Q1P1', **args)
    assert not calls
    with pytest.raises(pce.Changed, match='awaiting acceptance'): account_release.view(c,'Q1P1')
    assert 'accepted;' in account_amend.apply(c,'Q1P1',**args,resume=True)
    assert len(calls)==5
    assert 'accepted;' in account_amend.apply(c,'Q1P1',**args,resume=True)
    assert len(calls)==5
    for call in calls:
        shown = json.loads(call['prompt'].split('Allowed input files:\n')[1])
        if call['role'] in ('critic','fact-checker'):
            assert shown[pce.DRAFT] == candidate
            assert not any(n.startswith(('sources/internal/','reviews/')) for n in shown)
        if call['role']=='fact-checker':
            assert any(x['id']=='amendment-1' for x in json.loads(shown[pce.CLAIMS]))
    _script(monkeypatch, {'present/editor':[edited()], 'present_check/checker':[check()]})
    assert account_release.present(c,'Q1P1')=='CLEARED'
    assert account_release.release(c,'Q1P1',timestamp='20261019T170000Z')['status']=='RELEASED'
    assert all(pce_recovery.hashes(ed)[k]==v for k,v in before.items())
    assert pce.result(c,'Q1P1')['status']=='none'
    assert 'accepted_note' not in edit.status(c,'Q1P1')
    v = account_release.view(c,'Q1P1')
    acceptance = json.loads((paper.folder(v,'Q1P1')/'acceptance.json').read_text())
    assert acceptance['original_acceptance']['kind'].startswith('imported EVA2')
    assert (paper.folder(v,'Q1P1')/'paper.tex').read_text()==candidate


@pytest.mark.parametrize('gate', ['fact_checker','critic','editor'])
def test_failed_review_never_installs_or_renews(tmp_path, monkeypatch, gate):
    c, ed, candidate, args = packet(tmp_path)
    calls=script(monkeypatch,c,**{gate:['fail' if gate=='fact_checker' else 'revise']})
    assert 'review_required' in account_amend.apply(c,'Q1P1',**args,resume=True)
    n=len(calls)
    assert 'review_required' in account_amend.apply(c,'Q1P1',**args,resume=True)
    assert len(calls)==n
    with pytest.raises(pce.Changed,match='awaiting acceptance'): account_release.view(c,'Q1P1')


@pytest.mark.parametrize('change',['undeclared','baseline','evidence','outside','findings'])
def test_packet_refused_before_calls_or_activation(tmp_path,monkeypatch,change):
    c, ed, candidate, args=packet(tmp_path)
    pk=args['packet']; ch=json.loads((pk/'changes.json').read_text())
    if change=='undeclared':
        candidate += '%extra\n'; (pk/'account-candidate.tex').write_text(candidate); ch['candidate_sha256']=pce._sha(candidate)
    if change=='baseline': ch['baseline_sha256']='bad'
    if change=='findings': ch['changes'][0]['finding']='P9'
    (pk/'changes.json').write_text(json.dumps(ch))
    ev=json.loads((pk/'evidence.json').read_text())
    if change=='evidence': ev['source_files'][0]['sha256']='bad'
    if change=='outside': ev['source_files'][0]['path']=str(pk/'account-candidate.tex')
    (pk/'evidence.json').write_text(json.dumps(ev))
    monkeypatch.setattr(pce,'run',lambda *a,**k:pytest.fail('no calls'))
    with pytest.raises(pce.Changed):account_amend.apply(c,'Q1P1',**args,resume=True)
    assert not (ed/'account-amendment.json').exists()


def test_acceptance_tamper_and_non_openai_refused(tmp_path,monkeypatch):
    c, ed, candidate, args=packet(tmp_path)
    script(monkeypatch,c)
    account_amend.apply(c,'Q1P1',**args,resume=True)
    (ed/'account-amendments/definitions/review/result.json').write_text('{"status":"accepted"}')
    with pytest.raises(pce.Changed,match='changed'): account_release.view(c,'Q1P1')
    c.raw['refusal_fallback']={'backend':'claude'}
    with pytest.raises(pce.Changed,match='fallback'): account_amend.apply(c,'Q1P1',**args)


def test_interrupted_review_replays_calls_and_charges_once(tmp_path, monkeypatch):
    from pathfinder.thread import Stopped
    c, ed, candidate, args = packet(tmp_path)
    calls=script(monkeypatch,c)
    dispatch=pce._dispatch
    def interrupted(c,pair,role,prompt,seconds=None):
        if role=='critic': raise Stopped()
        return dispatch(c,pair,role,prompt,seconds=seconds)
    monkeypatch.setattr(pce,'_dispatch',interrupted)
    with pytest.raises(Stopped): account_amend.apply(c,'Q1P1',**args,resume=True)
    assert len(calls)==3
    monkeypatch.setattr(pce,'_dispatch',dispatch)
    assert 'accepted;' in account_amend.apply(c,'Q1P1',**args,resume=True)
    assert len(calls)==5


def test_cli_prepare_then_apply_uses_real_stub_transport(tmp_path):
    from pathfinder import cli
    c, ed, candidate, args=packet(tmp_path)
    argv=['--root',str(c.root),'account-amend','Q1P1','--id',args['identity'],
          '--packet',str(args['packet']),'--evidence-root',str(args['evidence_root']),'--reason',args['reason']]
    cli.main(argv)
    assert not list((ed/'account-amendments').rglob('dispatch/*.json'))
    cli.main(argv+['--apply'])
    v=account_release.view(c,'Q1P1',create=True)
    assert (paper.folder(v,'Q1P1')/'paper.tex').read_text()==candidate
    rows=list((ed/'account-amendments').rglob('dispatch/*.json'))
    assert len(rows)==5
    assert all(json.loads(p.read_text())['receipt']['backend']=='stub' for p in rows)


def test_stopped_campaign_prepares_but_does_not_call(tmp_path, monkeypatch):
    from pathfinder import runner
    c, ed, candidate, args=packet(tmp_path)
    monkeypatch.setattr(runner,'stopped',lambda c:True)
    monkeypatch.setattr(pce,'run',lambda *a,**k:pytest.fail('stopped'))
    assert account_amend.apply(c,'Q1P1',**args,resume=True).startswith('stopped')
    assert not (ed/'account-amendments/definitions/acceptance.json').exists()


def test_changed_packet_cannot_reuse_identity(tmp_path):
    c, ed, candidate, args=packet(tmp_path)
    account_amend.apply(c,'Q1P1',**args)
    args['reason']='different authority'
    with pytest.raises(pce.Changed,match='different inputs'):account_amend.apply(c,'Q1P1',**args)
