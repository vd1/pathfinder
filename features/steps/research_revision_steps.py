"""Offline regression coverage of real research orchestration and persistence."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from behave import given, when, then
from pathfinder import config, research, transport
from pathfinder.ledger import Ledger


DOC = '\\documentclass{article}\\begin{document}\n%s\\end{document}\n'
OLD = DOC % '\\section{Account}\nThe bound applies to the original finite sample.\n'
NEW = DOC % '\\section{Repaired account}\nThe corrected bound includes the variance term.\n'


def revision_setup(context, stage='verify', prior=True):
    temporary = tempfile.TemporaryDirectory(prefix='pathfinder-revision-')
    context.add_cleanup(temporary.cleanup)
    context.root = Path(temporary.name)
    context.c = config.Campaign(
        root=context.root, backend='claude', model='sonnet', scan_model='sonnet',
        peer_search=False, seats=1, cut=10, rounds=3,
        allowances={'peer_seconds': 1, 'peer_calls': 1, 'consolidate_seconds': 1, 'verify_seconds': 1},
        budget_usd=10, prices={}, scan_fulltext=None, raw={'repairs': 2},
    )
    for side in ('Q', 'P'):
        context.c.path(f'{side}.jsonl').write_text(json.dumps({
            'id': side.lower(), 'title': f'{side} source', 'abstract': f'{side} evidence', 'text': None,
        }) + '\n')
    context.d = research.prepare(context.c, 'Q1P1')
    context.note = context.d / 'Q1P1.tex'
    if prior:
        context.note.write_text(OLD)
    Ledger(context.d / 'ledger.jsonl').add('ada', 'finding', 'Finite sample result with variance correction.')
    state = research.status(context.c, 'Q1P1')
    state.update(stage=stage, status='running')
    (context.d / 'status.json').write_text(json.dumps(state))
    context.requests = []
    context.decisions = ['DRAFT']
    context.responses = [NEW]
    context.exception = None


# @exceptional-double: forced provider failure and interruption cannot be produced
# on demand. Specs explicitly require offline transport-boundary returns; real
# workflow, requests, ledger, files and restart state remain in use.
def controlled_transport(context, campaign, request):
    context.requests.append(request)
    if request.stage == 'peer':
        Ledger(request.cwd / 'ledger.jsonl').add(request.actor, 'finding', 'Next-round variance calculation.')
        result = {'text': 'Peer evidence recorded.', 'error': None, 'transport_failed': False}
    elif request.stage == 'verify':
        decision = context.decisions.pop(0) if context.decisions else 'DRAFT'
        result = {'text': json.dumps({'decision': decision, 'reason': 'Variance term', 'action': 'Include variance'}),
                  'error': None, 'transport_failed': False}
    elif request.stage == 'consolidate':
        response = context.responses.pop(0) if len(context.responses) > 1 else context.responses[0]
        result = dict(response) if isinstance(response, dict) else {'text': response, 'error': None, 'transport_failed': False}
    else:
        raise AssertionError(f'Unexpected provider stage: {request.stage}')
    result.update(seconds=0, cost=None, outcome='error' if result['error'] else 'completed',
                  raw_events=[json.dumps({'type': 'result', 'result': result['text'], 'is_error': bool(result['error'])})])
    transport._receipt(campaign, request.thread, request.stage, request.actor, request.model, result)
    return result


def revision_run(context):
    with patch.object(transport, 'execute', lambda c, r: controlled_transport(context, c, r)):
        try:
            context.result = research.run_thread(context.c, 'Q1P1')
        except (transport.TransportFailed, OSError, ValueError) as error:
            context.exception = error
            context.result = research.status(context.c, 'Q1P1')['status']


@given('pair "Q1P1" has an existing account and a verifier correction')
def existing_correction(context):
    revision_setup(context)
    context.decisions = ['REVISE', 'DRAFT']


@given('pair "Q1P1" has an existing account and an unanswered research question')
def existing_question(context):
    revision_setup(context)
    context.decisions = ['ITERATE', 'DRAFT']


@when('the research workflow receives a nonempty repair account after "REVISE"')
@when('the research workflow receives a nonempty next-round account after "ITERATE"')
def returned_revision(context):
    revision_run(context)


@then('the current account equals the returned repair account')
@then('the current account equals the returned next-round account')
@then('the current account equals the retained consolidation response')
def current_revision(context):
    assert context.note.read_text() == NEW, context.note.read_text()


@then('the previous account remains available as an immutable version')
@then('the older account remains available as an immutable version')
def immutable_account(context):
    versions = [p for p in context.d.rglob('*.tex') if p != context.note and p.read_text() == OLD]
    assert versions, 'No separate immutable version preserves previous account'
    snapshot = {p: p.read_bytes() for p in versions}
    revision_run(context)
    assert all(p.read_bytes() == content for p, content in snapshot.items())


@then('the next verifier receives the repaired account')
@then('the next verifier receives the next-round account')
def verifier_revision(context):
    requests = [r for r in context.requests if r.stage == 'verify']
    assert len(requests) >= 2
    assert NEW in requests[-1].prompt


@given('pair "Q1P1" has an older account and a retained successful consolidation response for its current round')
def retained_response(context):
    revision_setup(context, stage='consolidate')
    original_write = research._atomic_write
    context.interrupted = False

    class Interrupted(BaseException):
        pass

    # @exceptional-double: interrupt canonical-account publication after response
    # retention, a crash window impossible to request from a live provider.
    def interrupt_write(path, data):
        if path == context.note and data == NEW.encode():
            context.interrupted = True
            raise Interrupted()
        return original_write(path, data)

    with patch.object(research, '_atomic_write', interrupt_write):
        try:
            revision_run(context)
        except Interrupted:
            pass
    assert context.interrupted, 'Fresh consolidation response never reached account publication'
    assert context.note.read_text() == OLD
    context.requests = []


@when('the interrupted research workflow resumes')
def resume_revision(context):
    revision_run(context)


@then('recovery makes no new consolidation call')
def no_recovery_call(context):
    assert not [r for r in context.requests if r.stage == 'consolidate']


@when('every fresh repair response is empty')
def empty_repairs(context):
    context.responses = ['']
    revision_run(context)


@when('every fresh repair response reports a provider failure')
def failed_repairs(context):
    context.responses = [{'text': NEW, 'error': 'Provider request failed', 'transport_failed': False}]
    revision_run(context)


@then('consolidation is blocked without assessing the older account again')
def blocked_revision(context):
    assert context.result == 'BLOCKED', (context.result, str(context.exception))
    assert len([r for r in context.requests if r.stage == 'verify']) == 1
    assert research.status(context.c, 'Q1P1')['stage'] == 'consolidate'


@then('the existing account remains available for inspection')
def old_inspectable(context):
    assert context.note.read_text() == OLD


@given('a campaign sets "stage_attempts" to 1')
def one_attempt(context):
    revision_setup(context, stage='consolidate', prior=False)
    context.c.raw['stage_attempts'] = 1


@when('its consolidation response is empty or failed')
def single_attempt_responses(context):
    context.attempt_results = []
    for response in ('', {'text': NEW, 'error': 'Provider request failed', 'transport_failed': False}):
        revision_setup(context, stage='consolidate', prior=False)
        context.c.raw['stage_attempts'] = 1
        context.responses = [response]
        revision_run(context)
        context.attempt_results.append((context.result, len(context.requests)))


@then('consolidation is blocked after exactly one provider call')
def one_call(context):
    assert context.attempt_results == [('BLOCKED', 1), ('BLOCKED', 1)], context.attempt_results


@given('a campaign omits "stage_attempts"')
def default_attempts(context):
    revision_setup(context, stage='consolidate', prior=False)


@when('its first consolidation response is empty and its next response contains an account')
def retry_success(context):
    context.responses = ['', NEW]
    revision_run(context)


@then('consolidation succeeds after exactly two provider calls')
def default_retry(context):
    assert context.result == 'DRAFT', context.result
    assert len([r for r in context.requests if r.stage == 'consolidate']) == 2
    assert context.note.read_text() == NEW


@given('a campaign sets "stage_attempts" to an invalid non-positive or non-integer value')
def invalid_attempts(context):
    context.invalid_values = [0, -1, 1.5, '2', True, None]


@when('the research workflow starts')
def invalid_start(context):
    context.invalid_results = []
    for value in context.invalid_values:
        revision_setup(context, stage='consolidate', prior=False)
        manifest = {key: getattr(context.c, key) for key in ('backend', 'model', 'allowances', 'budget_usd')}
        manifest['stage_attempts'] = value
        context.c.path('campaign.json').write_text(json.dumps(manifest))
        try:
            context.c = config.load(context.root)
            revision_run(context)
        except ValueError as error:
            context.exception = error
        context.invalid_results.append((value, context.exception, len(context.requests)))


@then('configuration validation fails before any provider call')
def invalid_rejected(context):
    for value, error, calls in context.invalid_results:
        assert isinstance(error, ValueError) and 'stage_attempts' in str(error) and calls == 0, (value, error, calls)


EVIDENCE = {
    'ada/notes.tex': '\\section{Derivation}\nA complete variance calculation follows.\n',
    'emmy/check.py': 'from fractions import Fraction\nprint(Fraction(1, 3) + Fraction(2, 3))\n',
    'calculations/variance.json': '{"variance": 0.125, "sample_size": 128, "checked": true}\n',
}


@given('peer artefacts with calculation evidence beside an existing account')
def evidence_beside_account(context):
    revision_setup(context, stage='consolidate')
    for name, text in EVIDENCE.items():
        path = context.d / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    Ledger(context.d / 'ledger.jsonl').add('emmy', 'finding', 'Evidence: ' + ', '.join(EVIDENCE))


@when('the research workflow prepares its consolidation and verification requests')
def prepare_assessment_requests(context):
    revision_run(context)
    context.assessment = {r.stage: r for r in context.requests if r.stage in ('consolidate', 'verify')}
    assert set(context.assessment) == {'consolidate', 'verify'}, (context.result, str(context.exception))


@then('both requests have file tools and name the peer directories')
def assessment_tools(context):
    for request in context.assessment.values():
        assert request.tools is True and request.cwd == context.d, request.stage
        assert all(f'{peer}/' in request.prompt for peer in context.c.peers), request.stage


@then('neither request inlines the peer artefact contents')
def assessment_not_inlined(context):
    for request in context.assessment.values():
        assert not [name for name, text in EVIDENCE.items() if text in request.prompt], request.stage
