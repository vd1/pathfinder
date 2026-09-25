"""Offline regression coverage of real research orchestration and persistence."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from behave import given, when, then
from pathfinder import config, research, transport
from pathfinder.ledger import Ledger


OLD = '\\section{Account}\nThe bound applies to the original finite sample.\n'
NEW = '\\section{Repaired account}\nThe corrected bound includes the variance term.\n'


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
    original_write = Path.write_text
    context.interrupted = False

    class Interrupted(BaseException):
        pass

    # @exceptional-double: interrupt canonical-account publication after response
    # retention, a crash window impossible to request from a live provider.
    def interrupt_write(path, data, *args, **kwargs):
        if path == context.note and data == NEW:
            context.interrupted = True
            raise Interrupted()
        return original_write(path, data, *args, **kwargs)

    with patch.object(Path, 'write_text', interrupt_write):
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
    context.responses = [{'text': NEW, 'error': 'Provider request failed', 'transport_failed': True}]
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
    for response in ('', {'text': NEW, 'error': 'Provider request failed', 'transport_failed': True}):
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


def inline_evidence(context, stage):
    revision_setup(context, stage=stage)
    context.evidence = {
        'ada/notes.tex': '\\section{Derivation}\nA complete variance calculation follows.\n' + 'x = x + 1;\n' * 1800 + 'DERIVATION END\n',
        'emmy/check.py': 'from fractions import Fraction\nprint(Fraction(1, 3) + Fraction(2, 3))\n',
        'calculations/variance.json': '{"variance": 0.125, "sample_size": 128, "checked": true}\n',
    }
    for name, text in context.evidence.items():
        path = context.d / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    Ledger(context.d / 'ledger.jsonl').add('emmy', 'finding', 'Evidence: ada/notes.tex, emmy/check.py and calculations/variance.json')


@given('a tool-less consolidator has an existing account and peer artefacts with calculation evidence')
def consolidator_evidence(context):
    inline_evidence(context, 'consolidate')


@given('a tool-less verifier has a revised account and peer artefacts with calculation evidence')
def verifier_evidence(context):
    inline_evidence(context, 'verify')
    context.note.write_text(NEW)


@when('the research workflow prepares its consolidation request')
@when('the research workflow prepares its verification request')
def prepare_evidence_request(context):
    revision_run(context)
    assert context.requests, str(context.exception)
    context.request = context.requests[0]
    assert context.request.tools is False


@then('the request contains the complete prior account and peer artefact contents')
def complete_prior(context):
    assert OLD in context.request.prompt, 'Prior account absent from consolidator request'
    for name, content in context.evidence.items():
        assert content in context.request.prompt, f'Incomplete evidence: {name}'


@then('the request contains the complete current account and peer artefact contents')
def complete_current(context):
    assert NEW in context.request.prompt
    for name, content in context.evidence.items():
        assert content in context.request.prompt, f'Incomplete evidence: {name}'


@then('the request contains the complete calculation evidence with its source paths')
def complete_calculations(context):
    for name, content in context.evidence.items():
        assert name in context.request.prompt and content in context.request.prompt, name


@given('a tool-less assessment requires a peer artefact that cannot be read')
def unreadable_evidence(context):
    inline_evidence(context, 'consolidate')
    context.unreadable = 'ada/notes.tex'
    (context.d / context.unreadable).unlink()


@when('the research workflow prepares the assessment request')
def prepare_unreadable(context):
    if hasattr(context, 'alias_cases'):
        for case in context.alias_cases:
            revision_run(case)
    else:
        revision_run(context)


@then('the assessment is blocked before a provider call with the unreadable evidence identified')
def unreadable_blocked(context):
    state = research.status(context.c, 'Q1P1')
    assert state['status'] == 'BLOCKED', state
    assert not context.requests
    assert context.unreadable in state.get('reason', ''), state


def outside_evidence(context):
    revision_setup(context, stage='consolidate')
    context.outside = context.d.parent / 'Q2P1' / 'calculation.txt'
    context.outside.parent.mkdir()
    context.outside.write_text('Evidence owned by another investigation.\n')
    context.outside_reads = []
    original_read = Path.read_text

    # @exceptional-double: read observation proves internal ordering against real
    # files; spy delegates to original filesystem read without substitution.
    def observe_read(path, *args, **kwargs):
        if path.resolve() == context.outside.resolve():
            context.outside_reads.append(str(path))
        return original_read(path, *args, **kwargs)

    observer = patch.object(Path, 'read_text', observe_read)
    observer.start()
    context.add_cleanup(observer.stop)


@given('a tool-less assessment ledger references a calculation outside its investigation through parent traversal')
def traversal_evidence(context):
    outside_evidence(context)
    Ledger(context.d / 'ledger.jsonl').add('ada', 'finding', 'Calculation: ../Q2P1/calculation.txt')


@given('a tool-less assessment peer artefact or calculation path is a symlink to outside evidence')
def symlink_evidence(context):
    outside_evidence(context)
    (context.d / 'ada' / 'linked.txt').symlink_to(context.outside)
    calculations = context.d / 'calculations'
    calculations.mkdir()
    (calculations / 'linked.txt').symlink_to(context.outside)
    Ledger(context.d / 'ledger.jsonl').add('ada', 'finding', 'Calculation: calculations/linked.txt')


@then('the assessment is blocked before reading outside evidence or calling a provider')
def isolated_evidence(context):
    state = research.status(context.c, 'Q1P1')
    assert state['status'] == 'BLOCKED' and not context.outside_reads and not context.requests, {
        'status': state['status'], 'outside_reads': context.outside_reads,
        'provider_calls': len(context.requests),
    }


@given('a tool-less assessment references an internal evidence target through a symlink or parent traversal')
def internal_aliases(context):
    from types import SimpleNamespace
    context.alias_cases = []
    for kind in ('file symlink', 'directory symlink', 'parent traversal'):
        case = SimpleNamespace(add_cleanup=context.add_cleanup, kind=kind, alias_reads=[])
        revision_setup(case, stage='consolidate')
        target = case.d / 'calculations' / 'result.txt'
        target.parent.mkdir()
        target.write_text('Internal calculation result.\n')
        if kind == 'file symlink':
            alias = case.d / 'ada' / 'linked.txt'
            alias.symlink_to(target)
        elif kind == 'directory symlink':
            (case.d / 'ada' / 'linked').symlink_to(target.parent, target_is_directory=True)
            alias = case.d / 'ada' / 'linked' / 'result.txt'
        else:
            alias = case.d / 'ada' / '..' / 'calculations' / 'result.txt'
        case.alias = alias
        Ledger(case.d / 'ledger.jsonl').add('ada', 'finding', f'Calculation: {alias.relative_to(case.d)}')
        context.alias_cases.append(case)
    original_read = Path.read_text

    # @exceptional-double: delegated read spy records alias access ordering.
    def observe_alias(path, *args, **kwargs):
        for case in context.alias_cases:
            if path == case.alias:
                case.alias_reads.append(str(path))
        return original_read(path, *args, **kwargs)

    observer = patch.object(Path, 'read_text', observe_alias)
    observer.start()
    context.add_cleanup(observer.stop)


@then('the assessment is blocked before reading the aliased evidence or calling a provider')
def aliases_blocked(context):
    results = [{'kind': case.kind, 'status': research.status(case.c, 'Q1P1')['status'],
                'alias_reads': case.alias_reads, 'provider_calls': len(case.requests)}
               for case in context.alias_cases]
    assert all(row['status'] == 'BLOCKED' and not row['alias_reads'] and row['provider_calls'] == 0
               for row in results), results


def reference_cases(context):
    from types import SimpleNamespace
    context.reference_cases = []
    for stage in ('consolidate', 'verify'):
        case = SimpleNamespace(add_cleanup=context.add_cleanup, stage=stage, reads=[])
        revision_setup(case, stage=stage)
        context.reference_cases.append(case)
    context.reference_evidence = {}
    context.reference_provenance = []


def record_references(context, text):
    context.reference_provenance.append(text)
    for case in context.reference_cases:
        Ledger(case.d / 'ledger.jsonl').add('ada', 'finding', text)


def calculation_reference(context, name, content):
    context.reference_evidence[name] = content
    for case in context.reference_cases:
        path = case.d / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    record_references(context, f'Calculation: {name}')


@given('a research ledger cites "{first}" and "{second}" as bare DOIs and resolver URLs')
def cited_dois(context, first, second):
    reference_cases(context)
    context.dois = (first, second)
    record_references(context, f'Bibliography: {first}, https://doi.org/{first}; {second}, https://doi.org/{second}')


@given('the ledger references a readable local calculation artefact')
def readable_calculation(context):
    calculation_reference(context, 'calculations/results/variance.json', '{"variance": 0.125, "samples": 128}\n')


@given('a research ledger cites "{locator}" as the location of a published finding')
def scholarly_locator(context, locator):
    reference_cases(context)
    context.locator = locator
    record_references(context, f'The published finding appears in {locator}.')


@given('a research ledger records the command "{command}"')
def interpreter_command(context, command):
    reference_cases(context)
    context.command = command
    record_references(context, f'Command: {command}')


@given('the referenced calculation script is readable')
def readable_script(context):
    calculation_reference(context, 'ada/check_sector.py', 'from fractions import Fraction\nprint(Fraction(1, 3) + Fraction(2, 3))\n')


@given('a research ledger references calculation artefacts under "{nested}" and "{shared}" outside peer directories')
def non_peer_calculations(context, nested, shared):
    reference_cases(context)
    calculation_reference(context, f'{nested}/sector.json', '{"sector": 2, "checked": true}\n')
    calculation_reference(context, f'{shared}/derivation.tex', '\\section{Calculation}\n' + 'x = x + 1;\n' * 1800 + 'CALCULATION END\n')


@given('a research ledger references the missing local calculation "{name}"')
def missing_non_peer_calculation(context, name):
    reference_cases(context)
    record_references(context, f'Calculation: {name}')
    assert all(not (case.d / name).exists() for case in context.reference_cases)


@when('the workflow prepares tool-less consolidation and verification requests')
@when('the workflow prepares a tool-less assessment request')
def prepare_reference_requests(context):
    original_read = Path.read_text

    # @exceptional-double: delegated filesystem spy observes internal read
    # ordering; real local files and transport-controlled workflow remain in use.
    def observe_reference_read(path, *args, **kwargs):
        for case in context.reference_cases:
            if path.is_relative_to(case.d):
                case.reads.append(str(path.relative_to(case.d)))
        return original_read(path, *args, **kwargs)

    with patch.object(Path, 'read_text', observe_reference_read):
        for case in context.reference_cases:
            revision_run(case)


@then('both requests retain the DOI citations and complete local calculation contents')
@then('both requests retain the scholarly locator and complete local calculation contents')
@then('both requests contain the complete calculation script and command provenance')
@then('both requests contain every referenced local calculation artefact in full')
def complete_reference_requests(context):
    for case in context.reference_cases:
        requests = [request for request in case.requests if request.stage == case.stage]
        assert len(requests) == 1, (case.stage, research.status(case.c, 'Q1P1'))
        request = requests[0]
        assert request.tools is False
        for provenance in context.reference_provenance:
            assert provenance in request.prompt, (case.stage, provenance)
        for name, content in context.reference_evidence.items():
            assert name in request.prompt and content in request.prompt, (case.stage, name)


@then('no DOI or fragment of a resolver URL is read as a local file')
def citations_not_read(context):
    for case in context.reference_cases:
        assert not [name for name in case.reads if any(part in name for doi in context.dois for part in doi.split('/'))], case.reads


@then('the scholarly figure locator is not read as a local file')
def locator_not_read(context):
    for case in context.reference_cases:
        assert context.locator not in case.reads, case.reads


@then('no fragment of the interpreter path is read as local evidence')
def interpreter_not_read(context):
    interpreter = context.command.split()[0]
    for case in context.reference_cases:
        assert not [name for name in case.reads if any(part in name for part in interpreter.split('/') if part)], case.reads


@then('assessment blocks before provider dispatch and identifies "{name}"')
def missing_reference_blocks(context, name):
    for case in context.reference_cases:
        state = research.status(case.c, 'Q1P1')
        assert state['status'] == 'BLOCKED' and name in state.get('reason', ''), (case.stage, state)
        assert not case.requests, (case.stage, case.requests)
