"""External citations through real request preparation and local file fixtures."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from behave import given, when, then
from pathfinder import research
from pathfinder.ledger import Ledger
from eva_ledger_steps import PAIR, setup, reload_campaign, requests


CITED_PATH = 'ammo/msm/_msm.py'
CITED_URL = 'https://github.com/michellab/AMMo/blob/main/ammo/msm/_msm.py'


def declare(root, ledger, path=CITED_PATH, status='external'):
    text = f'External repository citation: {path}. Availability must remain explicit.'
    seq = ledger.add('ada', 'finding', text)
    record = {
        'document': 'ledger.jsonl', 'ledger_seq': seq, 'path': path,
        'url': CITED_URL, 'status': status,
        'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
    }
    declaration = root / 'external-references.json'
    declaration.write_text(json.dumps({'version': 1, 'references': [record]}))
    return record


@given('an EVA-minus ledger cites external "{path}" in a bound declaration')
def external_ledger(context, path):
    setup(context)
    context.citation = declare(context.d, context.ledger, path)
    context.cited_file = context.d / path
    assert not context.cited_file.exists()


@given('another attributed ledger entry is appended')
def append_entry(context):
    context.ledger.add('emmy', 'objection', 'Repository availability is separate from numerical validation.')


@given('the declared ledger entry text is changed after declaration')
def change_bound_text(context):
    rows = context.ledger.read()
    row = next(row for row in rows if row['seq'] == context.citation['ledger_seq'])
    row['text'] += ' Changed numerical interpretation.'
    context.ledger.path.write_text(''.join(json.dumps(row) + '\n' for row in rows))


@given('another ledger entry references missing local "{path}"')
def missing_local(context, path):
    assert not (context.d / path).exists()
    context.ledger.add('emmy', 'finding', f'Local calculation evidence: {path}')


def blocked(context, path):
    state = research.status(context.c, PAIR)
    assert state['status'] == 'BLOCKED', state
    assert path in state['reason'], state
    assert context.prepared == [], context.prepared
    return state


@then('Vera receives the ledger and its external citation declaration')
def direct_material(context):
    assert len(context.prepared) == 1, research.status(context.c, PAIR)
    request = context.prepared[0]
    assert request.stage == 'ledger_review', request.stage
    assert context.ledger.path.read_text() in request.prompt
    for field in ('document', 'path', 'url', 'status', 'text_sha256'):
        assert context.citation[field] in request.prompt, (field, request.prompt)
    for path, content in context.evidence.items():
        assert path in request.prompt and content in request.prompt


@then('the cited repository file is not required in the local workspace')
def no_local_file(context):
    assert not context.cited_file.exists()
    assert len(context.prepared) == 1, research.status(context.c, PAIR)
    assert research.status(context.c, PAIR)['status'] == 'running'


@then('research blocks before provider dispatch because the citation binding is stale')
def stale_binding(context):
    state = blocked(context, 'ledger.jsonl')
    reason = state['reason'].lower()
    assert any(word in reason for word in ('stale', 'digest', 'hash', 'binding')), state


@then('research blocks before provider dispatch and identifies "{path}"')
def missing_blocked(context, path):
    blocked(context, path)


@given('that cited workspace path is an alias to a file outside the thread')
def cited_alias(context):
    outside = context.root / 'outside-citation.py'
    outside.write_text('Outside citation contents must remain unread.\n')
    context.cited_file.parent.mkdir(parents=True)
    context.cited_file.symlink_to(outside)
    context.alias_reads = []
    originals = {name: getattr(Path, name) for name in ('read_text', 'read_bytes')}

    # @exceptional-double: delegated read spies observe internal ordering, for
    # which no independent external verifier exists. Every read stays real.
    def observe(name):
        def delegated(path, *args, **kwargs):
            if path == context.cited_file or path == outside:
                context.alias_reads.append(str(path))
            return originals[name](path, *args, **kwargs)
        return delegated

    for name in originals:
        observer = patch.object(Path, name, observe(name))
        context.add_cleanup(observer.stop)
        observer.start()


@then('research blocks before reading the aliased citation file')
def alias_blocked(context):
    state = blocked(context, context.citation['path'])
    assert 'alias' in state['reason'].lower(), state
    assert context.alias_reads == [], context.alias_reads


def joint_fixture(context, missing_sibling=False):
    setup(context, scheme='eva', imported=False)
    context.manifest['research_bundles'] = ['branches/external', 'branches/local']
    reload_campaign(context)
    external = context.d / 'branches' / 'external'
    external.mkdir(parents=True)
    context.citation = declare(external, Ledger(external / 'ledger.jsonl'), status='unavailable')
    local = context.d / 'branches' / 'local'
    local.mkdir(parents=True)
    Ledger(local / 'ledger.jsonl').add('emmy', 'finding', f'Local branch evidence: {CITED_PATH}')
    context.sibling_file = local / CITED_PATH
    context.sibling_content = '# Local branch calculation\nvariance = 0.125\n'
    if not missing_sibling:
        context.sibling_file.parent.mkdir(parents=True)
        context.sibling_file.write_text(context.sibling_content)


@given('joint EVA imports a branch with a bound unavailable external citation')
def unavailable_bundle(context):
    joint_fixture(context)


@when('Pathfinder prepares joint research')
def joint_requests(context):
    context.prepared = requests(context)


@then('the joint researcher receives the citation URL and unavailable status')
def joint_citation_visible(context):
    assert {request.actor for request in context.prepared} == {'ada', 'emmy'}, research.status(context.c, PAIR)
    for request in context.prepared:
        assert request.stage == 'peer'
        assert CITED_URL in request.prompt
        assert 'unavailable' in request.prompt
        assert context.citation['text_sha256'] in request.prompt


@then('the external citation is resolved only in its originating branch namespace')
def namespace_isolation(context):
    for request in context.prepared:
        assert 'branches/external/ledger.jsonl' in request.prompt
        assert f'branches/local/{CITED_PATH}' in request.prompt
        assert context.sibling_content in request.prompt
    # Same citation in another branch cannot satisfy missing local evidence.
    other = SimpleNamespace(add_cleanup=context.add_cleanup)
    joint_fixture(other, missing_sibling=True)
    other.prepared = requests(other)
    blocked(other, CITED_PATH)
