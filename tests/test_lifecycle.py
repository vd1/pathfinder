import fcntl
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile

import pytest
from pathfinder import lifecycle as l
from pathfinder.cli import main


def put(root, name, data=b'evidence\r\n'):
    p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
    return p


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / 'run'; root.mkdir()
    for name in ('threads/Q-P/ledger.jsonl', 'threads/Q-P/reopened/raw.json',
                 'receipts.jsonl', 'paper-pool/source.pdf', 'engine-freeze.json',
                 'publication/release/dated.tex', 'unknown.bin', '__pycache__/m.pyc'):
        put(root, name)
    return root


def test_retention_and_git(tree):
    subprocess.run(['git', 'init', '-q', str(tree)], check=True)
    put(tree, '.gitignore', b'paper-pool/\nunknown.bin\n')
    subprocess.run(['git', '-C', str(tree), 'add', 'receipts.jsonl'], check=True)
    rows = {r['path']: r for r in l.inventory(tree)['files']}
    assert rows['receipts.jsonl']['git'] == 'tracked'
    assert rows['paper-pool/source.pdf']['retained_but_ignored']
    assert rows['unknown.bin']['category'] == 'retain-unclassified'
    rules = l.ignore_rules(l.inventory(tree))
    assert '/__pycache__/m.pyc' in rules and 'source.pdf' not in rules
    assert [r['path'] for r in l.cleanup_plan(tree)['candidates']] == ['__pycache__/m.pyc']
    assert put(tree, 'threads/Q-P/__pycache__/e.pyc').exists()
    assert l.category(Path('threads/Q-P/__pycache__/e.pyc')) == 'retained-evidence'


def test_roundtrip(tree, tmp_path):
    before = l.inventory(tree)
    bundle = tmp_path / 'archive.tgz'
    receipt = l.archive(tree, bundle)
    assert l.inventory(tree) == before
    target = tmp_path / 'restored'
    l.restore(bundle, target, receipt['sha256'])
    assert l.inventory(target)['files'] == before['files']
    with pytest.raises(ValueError, match='new destination'):
        l.restore(bundle, target, receipt['sha256'])
    with pytest.raises(ValueError, match='external receipt'):
        l.restore(bundle, tmp_path / 'bad', '0' * 64)
    with pytest.raises(ValueError, match='outside'):
        l.archive(tree, tree / 'archive.tgz')


def test_busy_lock_and_orphan(tree, tmp_path):
    lock = put(tree, 'runner.lock', b'')
    with lock.open('rb') as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert l.cleanup_plan(tree)['ownership_blocker']
        with pytest.raises(RuntimeError, match='active campaign'):
            l.archive(tree, tmp_path / 'no.tgz')
    put(tree, 'active-calls/old.json', b'{}')
    with pytest.raises(RuntimeError, match='unresolved active-call'):
        l.archive(tree, tmp_path / 'no.tgz')
    assert not (tmp_path / 'no.tgz').exists()


def test_symlink_no_follow(tree, tmp_path):
    (tree / 'linked').symlink_to(tmp_path, target_is_directory=True)
    assert next(r for r in l.inventory(tree)['files'] if r['path'] == 'linked')['kind'] == 'symlink'
    with pytest.raises(ValueError, match='symlinks'):
        l.archive(tree, tmp_path / 'no.tgz')


def test_changed_snapshot_no_publication(tree, tmp_path, monkeypatch):
    original = l.inventory; count = 0
    def inventory(root):
        nonlocal count
        count += 1
        if count == 2:
            put(tree, 'new-evidence')
        return original(root)
    monkeypatch.setattr(l, 'inventory', inventory)
    with pytest.raises(RuntimeError, match='inventory changed'):
        l.archive(tree, tmp_path / 'no.tgz')
    assert not (tmp_path / 'no.tgz').exists()


@pytest.mark.parametrize('name', ['../escape', '/absolute', 'a/../../escape', '.git/config', 'a//b'])
def test_traversal(name):
    with pytest.raises(ValueError):
        l.safe_name(name)


def test_tampered_archive(tree, tmp_path):
    bundle = tmp_path / 'a.tgz'; l.archive(tree, bundle)
    bad = tmp_path / 'bad.tgz'
    with tarfile.open(bundle) as src, tarfile.open(bad, 'w:gz') as out:
        for member in src.getmembers():
            data = src.extractfile(member).read()
            if member.name == 'files/unknown.bin':
                data = b'x' * len(data)
            out.addfile(member, io.BytesIO(data))
    with pytest.raises(ValueError, match='hash mismatch'):
        l.verify_archive(bad)


def test_cli_readonly_no_config(tree, capsys):
    assert main(['--root', str(tree), 'lifecycle', 'cleanup']) == 0
    assert json.loads(capsys.readouterr().out)['dry_run'] is True
    assert not (tree / 'runner.lock').exists()


def test_archive_aware_ignores_exact_content(tree, tmp_path):
    bundle = tmp_path / 'a.tgz'; l.archive(tree, bundle)
    archived = l.verify_archive(bundle)
    assert '/paper-pool/source.pdf' in l.ignore_rules(l.inventory(tree), archived)
    put(tree, 'paper-pool/source.pdf', b'new scientific data')
    assert '/paper-pool/source.pdf' not in l.ignore_rules(l.inventory(tree), archived)
    assert '/unknown.bin' in l.ignore_rules(l.inventory(tree), archived)


def test_nested_git_worktree_status(tree):
    subprocess.run(['git', 'init', '-q', str(tree)], check=True)
    subprocess.run(['git', '-C', str(tree), 'add', 'threads/Q-P/ledger.jsonl'], check=True)
    rows = l.inventory(tree / 'threads')['files']
    assert next(r for r in rows if r['path'] == 'Q-P/ledger.jsonl')['git'] == 'tracked'


def test_archive_does_not_overwrite(tree, tmp_path):
    dest = put(tmp_path, 'keep.tgz', b'original')
    with pytest.raises(ValueError, match='already exists'):
        l.archive(tree, dest)
    assert dest.read_bytes() == b'original'


def test_thread_owner_blocks(tree, tmp_path):
    put(tree, 'threads/Q-P/lock', str(os.getpid()).encode())
    with pytest.raises(RuntimeError, match='active thread'):
        l.archive(tree, tmp_path / 'no.tgz')


@pytest.mark.parametrize('kind', ['duplicate', 'symlink', 'traversal'])
def test_archive_member_attacks(tree, tmp_path, kind):
    bundle = tmp_path / 'good.tgz'; l.archive(tree, bundle)
    bad = tmp_path / 'bad.tgz'
    with tarfile.open(bundle) as src, tarfile.open(bad, 'w:gz') as out:
        for member in src.getmembers():
            out.addfile(member, io.BytesIO(src.extractfile(member).read()))
        extra = tarfile.TarInfo('files/unknown.bin' if kind == 'duplicate' else 'files/../../escape')
        if kind == 'symlink':
            extra.type = tarfile.SYMTYPE; extra.linkname = '/etc/passwd'
        out.addfile(extra, io.BytesIO(b''))
    with pytest.raises(ValueError):
        l.restore(bad, tmp_path / 'restored', l.file_digest(bad))
    assert not (tmp_path / 'restored').exists()


def test_exact_ignore_metacharacters(tree):
    put(tree, '__pycache__/a[1]*?.pyc')
    rules = l.ignore_rules(l.inventory(tree))
    assert r'/__pycache__/a\[1\]\*\?.pyc' in rules
