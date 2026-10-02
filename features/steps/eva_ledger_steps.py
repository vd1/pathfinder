"""Real request preparation, retained-response ingestion, and ledger transitions.

Provider output is input to the response-ingestion boundary. No provider, CLI,
transport, or model execution is replaced. Model quality belongs to sandbox
verification; these scenarios specify orchestration of supplied review text.
"""
import json
import tempfile
from pathlib import Path

from behave import given, when, then
from pathfinder import config, research
from pathfinder.ledger import Ledger

PAIR = 'Q1P1'
ACCOUNT = '\\section{Account}\nThe variance bound requires a finite second moment.\n'
REPAIR = '\\section{Repaired account}\nThe finite second moment is an explicit premise.\n'
QUESTION = 'Compute the variance term for the finite sample.'
CORRECTION = 'State the finite second moment premise in the ledger argument.'
DEFERRED = 'The experimental covariance matrix has not been supplied.'


def setup(context, scheme='direct_eva', imported=True, rounds=2, reviews=4):
    temporary = tempfile.TemporaryDirectory(prefix='pathfinder-eva-ledger-')
    context.add_cleanup(temporary.cleanup)
    context.root = Path(temporary.name)
    context.manifest = {
        'backend': 'claude', 'model': 'sonnet', 'peer_search': False,
        'seats': 1, 'cut': 10, 'rounds': rounds, 'budget_usd': 10,
        'allowances': {'peer_seconds': 60, 'peer_calls': 1,
                       'consolidate_seconds': 60, 'verify_seconds': 60},
        'research_scheme': scheme, 'imported_research': imported,
        'ledger_reviews': reviews, 'inline_papers': True, 'inline_ledger': True,
        'inline_evidence': True,   # these scenarios specify inlined evidence; reference mode is covered by tests/test_agent_workspace.py
        'peers': ['emmy', 'ada'], 'repairs': 2,
    }
    reload_campaign(context)
    for side, title, abstract in (
        ('Q', 'Finite-sample variance bounds', 'The variance bound assumes finite second moment.'),
        ('P', 'Experimental covariance estimation', 'The estimator needs the observed covariance matrix.'),
    ):
        context.c.path(f'{side}.jsonl').write_text(json.dumps({
            'id': side.lower(), 'title': title, 'abstract': abstract, 'text': None,
        }) + '\n')
    # Imported research precedes preparation, as in an actual copied branch.
    context.d = context.c.thread_dir(PAIR)
    context.d.mkdir(parents=True)
    context.ledger = Ledger(context.d / 'ledger.jsonl')
    context.evidence = {}
    if imported:
        add_research(context, 'Imported finite-sample calculation.')
    research.prepare(context.c, PAIR)
    context.note = context.d / f'{PAIR}.tex'
    context.request_batches = []
    context.saved = []
    context.exception = None


def reload_campaign(context):
    (context.root / 'campaign.json').write_text(json.dumps(context.manifest))
    context.c = config.load(context.root)


def add_research(context, text):
    evidence = context.d / 'calculations' / 'variance.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    content = '{"variance": 0.125, "sample_size": 128}\n'
    evidence.write_text(content)
    context.evidence['calculations/variance.json'] = content
    context.ledger.add('emmy', 'finding', text + ' Evidence: calculations/variance.json')
    context.ledger.add('ada', 'objection', 'The covariance matrix is required to test this premise.')


def requests(context):
    """Prepare genuine model requests and apply retained responses, without dispatch."""
    batch = research.next_requests(context.c, PAIR)
    assert isinstance(batch, list), batch
    context.request_batches.append(batch)
    return batch


def retain(context, request, value):
    text = value if isinstance(value, str) else json.dumps(value)
    result = {'text': text, 'error': None, 'transport_failed': False,
              'seconds': 0, 'cost': None, 'outcome': 'completed'}
    research.retain_response(context.c, PAIR, request, result)
    context.saved.append((request, text))
    return text


def review_request(context):
    batch = requests(context)
    assert len(batch) == 1, [(r.stage, r.actor) for r in batch]
    assert batch[0].stage in ('ledger_review', 'verify'), batch[0].stage
    context.review_request = batch[0]
    context.ledger_before_review = context.ledger.read()
    return batch[0]


def apply_review(context, value):
    request = review_request(context)
    context.review_value = value
    context.review_text = retain(context, request, value)
    context.after_review = requests(context)


def finish_peers(context, batch=None):
    batch = requests(context) if batch is None else batch
    assert {r.actor for r in batch} == {'emmy', 'ada'}, [(r.stage, r.actor) for r in batch]
    assert all(r.stage == 'peer' for r in batch)
    for request in batch:
        context.ledger.add(request.actor, 'finding', 'New derivation: the second moment is finite.')
        retain(context, request, 'The new derivation is recorded on the shared ledger.')
    return requests(context)


def response(decision='ITERATE'):
    return {'decision': decision, 'reason': 'The variance premise needs attention.',
            'requests': [{'id': 'variance-premise', 'action': decision,
                          'text': CORRECTION if decision == 'REVISE' else QUESTION}],
            'dispositions': []}


def review_rows(context):
    return [row for row in context.ledger.read() if row['kind'] == 'review']


def outcome(context):
    return research.export_outcome(context.c, PAIR)


def data_text(value):
    return json.dumps(value, sort_keys=True)


def scientific_absent(value):
    assert value.get('scientific_verdict') is None, value
    assert value.get('verdict') not in ('DRAFT', 'ACCEPT', 'PAUSE', 'REJECT'), value


@given('an EVA-minus investigation with imported peer research and its evidence')
@given('an EVA-minus investigation awaiting review with research allowance remaining')
@given('an EVA-minus investigation awaiting review')
def imported(context):
    setup(context)


@when('Pathfinder prepares its first Vera review')
def first_review(context):
    context.prepared = requests(context)


@then('Vera receives both papers and the complete attributed research ledger')
def complete_review(context):
    assert len(context.prepared) == 1
    request = context.prepared[0]
    assert request.stage == 'ledger_review', request.stage
    for side in 'QP':
        assert (context.d / 'inputs' / f'{side}.txt').read_text() in request.prompt
    for row in context.ledger.read():
        assert row['actor'] in request.prompt and row['text'] in request.prompt
    assert (context.d / 'ledger.jsonl').read_text() in request.prompt


@then('Vera receives all referenced peer evidence without a consolidated account')
def complete_peer_evidence(context):
    for name, content in context.evidence.items():
        assert name in context.prepared[0].prompt and content in context.prepared[0].prompt
    assert not context.note.exists()
    assert all(r.stage != 'consolidate' for batch in context.request_batches for r in batch)


@given('a fresh EVA-minus investigation with two papers')
def fresh(context):
    setup(context, imported=False)


@when('its peer research round finishes')
def first_peers(context):
    context.prepared = finish_peers(context)


@then('its next stage is Vera ledger review')
def next_review(context):
    assert len(context.prepared) == 1 and context.prepared[0].stage == 'ledger_review'


@then('its thread contains no consolidated account')
def no_account(context):
    assert not context.note.exists()


@when('Vera requests REVISE of a ledger argument from existing evidence')
def revise_ledger(context):
    apply_review(context, response('REVISE'))


@when('Vera requests ITERATE with a concrete research gap')
def iterate_ledger(context):
    value = response()
    if context.manifest['research_scheme'] == 'eva':
        value['action'] = QUESTION
    apply_review(context, value)


@then('the review is appended to the ledger with its reviewed evidence identity')
def attributable_review(context):
    rows = review_rows(context)
    assert len(rows) == 1, rows
    row = rows[0]
    assert row['actor'] in ('vera', 'verifier'), row
    payload = json.loads(row['text'])
    assert payload['review_id'] == context.review_request.identity, payload
    assert isinstance(payload['evidence_id'], str) and len(payload['evidence_id']) >= 32, payload
    assert payload['response'] == context.review_value, payload
    assert context.ledger.read()[:len(context.ledger_before_review)] == context.ledger_before_review


@then('Emmy and Ada receive the correction request before the next direct review')
@then('Emmy and Ada receive the investigation request before the next direct review')
def peers_receive_request(context):
    batch = context.after_review
    assert {r.actor for r in batch} == {'emmy', 'ada'}
    for request in batch:
        assert request.stage == 'peer'
        assert context.review_value['requests'][0]['text'] in request.prompt
    following = finish_peers(context, batch)
    assert len(following) == 1 and following[0].stage == 'ledger_review'
    assert not context.note.exists()


def active_request(context, deferred=False):
    setup(context, rounds=3)
    apply_review(context, response())
    context.first_review = review_rows(context)[0]
    if deferred:
        context.ledger.add('ada', 'intention', f'Explicitly deferred request variance-premise: {DEFERRED}')
    finish_peers(context, context.after_review)


@given('an EVA-minus investigation with an active review request')
def active(context):
    active_request(context)


@given('an EVA-minus investigation with all previous review requests resolved or explicitly deferred')
def deferred(context):
    active_request(context, deferred=True)


@when('Vera returns no further actionable requests')
def no_further(context):
    apply_review(context, {'requests': [], 'dispositions': [
        {'id': 'variance-premise', 'status': 'deferred', 'reason': DEFERRED}]})
    context.branch_outcome = outcome(context)


@then('the branch is ready for handoff because no further requests remain')
def ready_no_requests(context):
    value = context.branch_outcome
    assert value['status'] == 'HANDOFF', value
    assert value['handoff_reason'] == 'no_further_requests', value


@then('the handoff preserves deferred objections without a scientific verdict')
def deferred_retained(context):
    value = context.branch_outcome
    assert DEFERRED in data_text(value) and 'variance-premise' in data_text(value)
    assert QUESTION in data_text(context.ledger.read())
    scientific_absent(value)


@given('an EVA-minus investigation with no research rounds remaining')
def no_rounds(context):
    setup(context, rounds=0)


@then('the branch is ready for handoff because its allowance is exhausted')
def ready_exhausted(context):
    value = outcome(context)
    assert value['status'] == 'HANDOFF', value
    assert value['handoff_reason'] == 'research_allowance_exhausted', value


@then('the handoff preserves the unanswered request without a scientific verdict')
def unanswered(context):
    value = outcome(context)
    assert QUESTION in data_text(value) and 'variance-premise' in data_text(value)
    scientific_absent(value)


@when('Vera returns no new requests and omits disposition of the active request')
def missing_disposition(context):
    apply_review(context, {'requests': [], 'dispositions': []})


@when('the retained Vera response has no valid request list')
def invalid_review(context):
    apply_review(context, 'There are no further issues; research looks complete.')


@when('Vera returns PAUSE instead of a request review')
def terminal_minus(context):
    apply_review(context, {'decision': 'PAUSE', 'reason': DEFERRED})


@then('Pathfinder records an operational review error rather than a handoff')
def operational_error(context):
    state = research.status(context.c, PAIR)
    assert state['status'] == 'BLOCKED', state
    assert state.get('reason'), state
    assert not context.after_review
    def contains(value):
        if isinstance(value, dict):
            return any(contains(v) for v in value.values())
        if isinstance(value, list):
            return any(contains(v) for v in value)
        return value == context.review_text
    assert any(contains(json.loads(p.read_text())) for p in context.d.rglob('*.json'))
    scientific_absent(outcome(context))


@when('a later Vera review defers that request with a missing-input reason')
def later_deferral(context):
    apply_review(context, {'requests': [], 'dispositions': [
        {'id': 'variance-premise', 'status': 'deferred', 'reason': DEFERRED}]})


@then('the ledger retains the original request and its attributed deferral')
def preserved_deferral(context):
    rows = review_rows(context)
    assert len(rows) == 2 and rows[0] == context.first_review, rows
    assert QUESTION in rows[0]['text'] and DEFERRED in rows[1]['text']
    assert all(row['actor'] in ('vera', 'verifier') for row in rows)
    assert 'variance-premise' in rows[0]['text'] and 'variance-premise' in rows[1]['text']
    assert json.loads(rows[0]['text'])['review_id'] != json.loads(rows[1]['text'])['review_id']


@given('a completed Vera response whose feedback is already on the ledger')
def completed_feedback(context):
    setup(context)
    request = review_request(context)
    retain(context, request, {'requests': [], 'dispositions': []})
    context.before_transition = (context.d / 'status.json').read_bytes()
    requests(context)
    assert len(review_rows(context)) == 1
    context.completed_rows = context.ledger.read()


@given('a restart before the review transition was persisted')
def interrupted_transition(context):
    # Persisted response and append-only ledger survive; status is crash-old.
    (context.d / 'status.json').write_bytes(context.before_transition)
    context.c = config.load(context.root)


@when('Pathfinder resumes the investigation')
def resume(context):
    context.resumed_requests = requests(context)


@then('the review occurs once in the ledger')
def once(context):
    assert context.ledger.read() == context.completed_rows
    assert len(review_rows(context)) == 1


@then('the retained response is applied without another model dispatch')
def retained_no_dispatch(context):
    assert context.resumed_requests == []
    assert outcome(context)['status'] == 'HANDOFF'


@given('a Vera response bound to a research ledger and evidence snapshot')
def bound_review(context):
    setup(context)
    request = review_request(context)
    retain(context, request, {'requests': [], 'dispositions': []})


@when('the evidence changes before that response is applied')
def changed_evidence(context):
    (context.d / 'calculations' / 'variance.json').write_text('{"variance": 0.25, "sample_size": 128}\n')
    context.stale_requests = requests(context)


@then('Pathfinder blocks the stale response before a research transition')
def stale_blocked(context):
    state = research.status(context.c, PAIR)
    assert state['status'] == 'BLOCKED', state
    assert 'stale' in state['reason'].lower() or 'evidence' in state['reason'].lower()
    assert not context.stale_requests and not review_rows(context)
    assert not context.note.exists()


@given('an EVA-minus investigation whose first review requested REVISE')
def first_revise(context):
    setup(context)
    context.first_peer_calls = []
    apply_review(context, response('REVISE'))
    context.earlier_calls = [context.review_request]


@when('the next research and review cycle is prepared')
def next_cycle(context):
    context.earlier_calls.extend(context.after_review)
    second_review = finish_peers(context, context.after_review)
    context.later_calls = list(second_review)
    retain(context, second_review[0], {'decision': 'ITERATE', 'requests': [
        {'id': 'covariance-estimate', 'action': 'ITERATE', 'text': 'Derive the covariance estimator.'}],
        'dispositions': [{'id': 'variance-premise', 'status': 'resolved',
                          'reason': 'Finite second moment established.'}]})
    context.later_calls.extend(requests(context))


@then('its calls have identities distinct from the earlier review cycle')
def distinct_identities(context):
    assert {r.identity for r in context.earlier_calls}.isdisjoint(r.identity for r in context.later_calls)
    all_calls = context.earlier_calls + context.later_calls
    assert len({r.identity for r in all_calls}) == len(all_calls)
    assert any(r.stage == 'peer' for r in context.later_calls)


@given('an EVA-minus ledger referencing a missing calculation output')
def missing_evidence(context):
    setup(context)
    context.manifest['strict_evidence'] = True
    reload_campaign(context)
    context.missing = 'calculations/missing-covariance.json'
    context.ledger.add('ada', 'finding', f'Calculation: {context.missing}')


@then('the review is blocked before a provider call with the missing path identified')
def evidence_blocked(context):
    state = research.status(context.c, PAIR)
    assert state['status'] == 'BLOCKED' and context.missing in state['reason'], state
    assert not context.prepared


def bundles(context):
    context.manifest['research_bundles'] = [f'branches/branch-{n}' for n in (1, 2, 3)]
    reload_campaign(context)
    context.bundle_material = {}
    for n, name in enumerate(context.manifest['research_bundles'], 1):
        root = context.d / name
        root.mkdir(parents=True)
        ledger = Ledger(root / 'ledger.jsonl')
        ledger.add('ada', 'finding', f'Branch {n} covariance claim. Evidence: calculations/value.json')
        calculation = root / 'calculations' / 'value.json'
        calculation.parent.mkdir()
        calculation.write_text(json.dumps({'branch': n, 'variance': n / 8}))
        for file in (root / 'ledger.jsonl', calculation):
            context.bundle_material[str(file.relative_to(context.d))] = file.read_text()
    context.bundle_bytes = {name: (context.d / name).read_bytes() for name in context.bundle_material}


@given('a joint EVA investigation with three namespaced frozen branch bundles')
def joint(context):
    setup(context, scheme='eva', imported=False)
    bundles(context)


@when('Pathfinder prepares peer research and synthesis and scientific verification')
def joint_stages(context):
    peers = requests(context)
    consolidation = finish_peers(context, peers)
    assert len(consolidation) == 1 and consolidation[0].stage == 'consolidate'
    retain(context, consolidation[0], ACCOUNT)
    verification = requests(context)
    assert len(verification) == 1 and verification[0].stage == 'verify'
    context.joint_requests = peers + consolidation + verification


@then('each stage receives all three ledgers and their referenced evidence')
@then('it includes those thread-relative bundle directories with their original reference namespaces')
def all_bundles(context):
    for request in context.joint_requests:
        for name, content in context.bundle_material.items():
            assert name in request.prompt and content in request.prompt, (request.stage, name)


@then('the original branch bundles remain unchanged')
def immutable_bundles(context):
    assert context.bundle_bytes == {name: (context.d / name).read_bytes() for name in context.bundle_bytes}


@when('Pathfinder prepares the peer research instructions')
@when('Pathfinder prepares the research evidence for that investigation')
def peer_instructions(context):
    context.joint_requests = requests(context)
    assert {r.actor for r in context.joint_requests} == {'emmy', 'ada'}


@then('the instructions require investigating disagreements and new connections')
def investigative_instructions(context):
    for request in context.joint_requests:
        prompt = request.prompt.lower()
        assert 'disagreement' in prompt and 'new connection' in prompt


@then('the instructions distinguish inherited evidence from new derivations and conjectures')
def inherited_instructions(context):
    for request in context.joint_requests:
        prompt = request.prompt.lower()
        assert 'inherited' in prompt and 'derivation' in prompt and 'conjecture' in prompt


def synthesised(context, rounds=2):
    setup(context, scheme='eva', imported=False, rounds=rounds)
    consolidation = finish_peers(context)
    assert len(consolidation) == 1 and consolidation[0].stage == 'consolidate'
    retain(context, consolidation[0], ACCOUNT)
    prepared = requests(context)
    assert len(prepared) == 1 and prepared[0].stage == 'verify'
    assert context.note.read_text() == ACCOUNT


@given('an EVA investigation with a synthesised account awaiting verification')
def eva_verify(context):
    synthesised(context)


@given('an EVA investigation with a synthesised account and no research rounds remaining')
def eva_exhausted(context):
    synthesised(context, rounds=1)


@when('Vera returns PAUSE with a missing-input reason')
def eva_pause(context):
    apply_review(context, {'decision': 'PAUSE', 'reason': DEFERRED, 'action': 'Supply covariance matrix.'})


@then('the full review is appended to the ledger exactly once')
def full_review(context):
    rows = review_rows(context)
    assert len(rows) == 1, rows
    assert json.loads(rows[0]['text'])['response'] == context.review_value, rows
    requests(context)
    assert review_rows(context) == rows


@then('the existing PAUSE scientific ending is preserved')
def pause_preserved(context):
    assert research.status(context.c, PAIR)['status'] == 'PAUSE'
    assert DEFERRED in data_text(outcome(context))


@then('the existing PAUSE-ON-ITERATE ending retains the unanswered request')
def iterate_preserved(context):
    assert research.status(context.c, PAIR)['status'] == 'PAUSE-ON-ITERATE'
    assert QUESTION in data_text(outcome(context))


@given('an EVA investigation whose scientific verifier returns DRAFT')
def draft(context):
    synthesised(context)
    apply_review(context, {'decision': 'DRAFT', 'reason': 'The stated bound follows.', 'action': ''})


@when('its composable research outcome is exported')
def exported(context):
    context.exported = outcome(context)


@then('the public scientific verdict is ACCEPT')
def accepted(context):
    assert context.exported['scientific_verdict'] == 'ACCEPT', context.exported


@then('the original verifier decision remains DRAFT in provenance')
def draft_provenance(context):
    assert 'DRAFT' in data_text(context.exported['provenance'])
    assert research.status(context.c, PAIR)['status'] == 'DRAFT'


@given('an ordinary EVA investigation awaiting research consolidation')
def ordinary(context):
    setup(context, scheme='eva', imported=False)
    # Omission preserves the ordinary, existing campaign configuration.
    del context.manifest['research_scheme']
    del context.manifest['imported_research']
    del context.manifest['ledger_reviews']
    reload_campaign(context)
    context.consolidation = finish_peers(context)


@when('Vera requests REVISE of the returned account using existing evidence')
def revise_account(context):
    retain(context, context.consolidation[0], ACCOUNT)
    requests(context)
    apply_review(context, {'decision': 'REVISE', 'reason': 'The premise is implicit.', 'action': CORRECTION})


@then('Emmy repairs the account before scientific verification')
def emmy_repairs(context):
    assert len(context.after_review) == 1
    repair = context.after_review[0]
    assert repair.stage == 'consolidate' and repair.actor == 'emmy'
    assert CORRECTION in repair.prompt and ACCOUNT in repair.prompt
    retain(context, repair, REPAIR)
    context.after_repair = requests(context)
    assert len(context.after_repair) == 1 and context.after_repair[0].stage == 'verify'
    assert context.note.read_text() == REPAIR and REPAIR in context.after_repair[0].prompt


@then('no additional peer research occurs for that repair')
def no_extra_peers(context):
    assert all(r.stage != 'peer' for r in context.after_review + context.after_repair)


@given('an EVA-minus investigation whose research advanced after its latest review')
def research_advanced(context):
    setup(context, reviews=1)
    apply_review(context, response())
    assert {r.actor for r in context.after_review} == {'emmy', 'ada'}
    for request in context.after_review:
        context.ledger.add(request.actor, 'finding', 'Latest derivation is newer than Vera review.')
        retain(context, request, 'Latest derivation recorded.')
    context.latest_seq = context.ledger.latest_substantive()


@given('no Vera calls remain')
def no_reviews(context):
    assert context.manifest['ledger_reviews'] == 1 and len(review_rows(context)) == 1


@when('Pathfinder advances the branch')
def advance(context):
    context.advanced_requests = requests(context)
    context.branch_outcome = outcome(context)


@then('the branch hands off the latest research with an explicit unreviewed-head marker')
def unreviewed_head(context):
    value = context.branch_outcome
    assert value['status'] == 'HANDOFF', value
    assert value['handoff_reason'] == 'review_allowance_exhausted', value
    assert value['unreviewed_head'] is True, value
    assert value['ledger_head'] == context.latest_seq, value
    assert not context.advanced_requests


@then('no scientific verdict is inferred')
def no_verdict(context):
    scientific_absent(context.branch_outcome)


@given('a campaign configuration with research_scheme "{scheme}"')
def configured(context, scheme):
    setup(context, scheme=scheme, imported=scheme == 'direct_eva')


@given('imported_research is true with rounds 2 and ledger_reviews 4')
def configured_limits(context):
    assert context.c.raw['imported_research'] is True
    assert context.c.rounds == 2 and context.c.raw['ledger_reviews'] == 4


@when('the standard research entry point opens the investigation')
def standard_entry(context):
    # A real operator stop prevents provider execution at the first dispatch.
    context.standard_result = research.run_thread(context.c, PAIR, stop=lambda: True)
    context.prepared = requests(context)


@then('it starts direct ledger review with at most two new peer rounds and four review calls')
def configured_start(context):
    assert len(context.prepared) == 1 and context.prepared[0].stage == 'ledger_review'
    calls = 0
    rounds = 0
    current = context.prepared
    while current:
        assert calls <= 4 and rounds <= 2, (calls, rounds)
        if current[0].stage == 'ledger_review':
            assert len(current) == 1
            calls += 1
            value = response()
            value['requests'][0]['id'] = f'variance-premise-{calls}'
            if calls > 1:
                value['dispositions'] = [{'id': f'variance-premise-{calls - 1}', 'status': 'resolved',
                                           'reason': 'The preceding derivation addressed this request.'}]
            retain(context, current[0], value)
            current = requests(context)
        else:
            rounds += 1
            current = finish_peers(context, current)
    assert 0 < calls <= 4 and rounds == 2, (calls, rounds)
    assert outcome(context)['status'] == 'HANDOFF'


@given('research_bundles lists "branches/branch-1", "branches/branch-2", and "branches/branch-3"')
def configured_bundles(context):
    bundles(context)


@given('an EVA-minus investigation ready for handoff')
def runner_handoff(context):
    setup(context)
    apply_review(context, {'requests': [], 'dispositions': []})
    assert outcome(context)['status'] == 'HANDOFF'
    context.c.path('shortlist.json').write_text(json.dumps({'pairs': [{'pair_id': PAIR}]}))
    context.handoff_ledger = context.ledger.read()


@when('the campaign runner completes that investigation')
def complete_branch(context):
    from unittest.mock import patch
    from pathfinder import edit, runner

    # @exceptional-double: negative internal-wiring assertion, with no external
    # verifier. The forbidden editing edge raises before it can invoke a model;
    # real research, runner locking, admission, and persistence remain in use.
    def forbidden_edit(*args, **kwargs):
        raise AssertionError('Campaign runner invoked account editing for an EVA-minus handoff')

    with patch.object(edit, 'run', forbidden_edit):
        context.runner_result = runner._work(context.c, PAIR)
    context.pending = runner.pending(context.c)


@then('it records the branch handoff without invoking account editing')
def runner_preserves_handoff(context):
    assert context.runner_result == 'HANDOFF'
    assert research.status(context.c, PAIR)['status'] == 'HANDOFF'
    assert outcome(context)['status'] == 'HANDOFF'
    assert context.ledger.read() == context.handoff_ledger
    assert not context.note.exists()
    assert PAIR not in context.pending, context.pending
