"""The release gate: every supported deployment passes against this candidate, and nothing is skipped.

    uv run python scripts/release_check.py [--notes RELEASE_NOTES.md]

Records the candidate commit and requires a clean tree, runs the whole suite with PATHFINDER_RELEASE=1 and the broad behave suite (so a
missing or mispinned deployment checkout fails instead of skipping), then requires the same commit and a
clean tree afterwards. It fails if any test failed, errored or was skipped, or if a supported deployment's
contract did not pass: a contract names a test file (every test in it must pass, and at least one must run)
or one exact test node (parameterized cases of it count, all of which must pass). Release notes are written
only when every check passes, and state each deployment's actual result. It never tags."""
import argparse, os, subprocess, sys, tempfile, tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def node_ids(junit: Path, root: Path = ROOT) -> dict:
    """pytest node id -> "passed", "skipped" or "failed", from a JUnit report. The classname is split into
    the test file and any classes by finding the longest prefix that is a file under root."""
    out = {}
    for case in ET.parse(junit).getroot().iter("testcase"):
        parts = case.get("classname", "").split(".")
        for i in range(len(parts), 0, -1):
            path = "/".join(parts[:i]) + ".py"
            if (root / path).is_file():
                node = "::".join([path, *parts[i:], case.get("name")])
                break
        else:
            node = f"{case.get('classname')}::{case.get('name')}"
        if case.find("skipped") is not None:
            out[node] = "skipped"
        elif case.find("failure") is not None or case.find("error") is not None:
            out[node] = "failed"
        else:
            out[node] = "passed"
    return out


def contract_result(contract: str, nodes: dict) -> str:
    """passed, failed, skipped or missing: the contract's tests, matched by exact file or exact node id."""
    if "::" in contract:
        hits = [s for n, s in nodes.items() if n == contract or n.startswith(contract + "[")]
    else:
        hits = [s for n, s in nodes.items() if n.split("::")[0] == contract]
    if not hits:
        return "missing"
    for state in ("failed", "skipped"):
        if state in hits:
            return state
    return "passed"


def evaluate(nodes: dict, returncode: int, deployments: dict, before: tuple, after: tuple, behave_returncode=0) -> tuple[list, dict]:
    """(problems, per-deployment result). before and after are (commit, clean)."""
    problems = []
    if not before[1]:
        problems.append("the working tree had uncommitted changes before the run")
    if after != before:
        problems.append(f"the candidate changed during the run: {before} -> {after}")
    if returncode:
        problems.append(f"pytest exited {returncode}")
    if behave_returncode:
        problems.append(f"the behave broad suite exited {behave_returncode}")
    problems += [f"{state} in a release run: {n}" for n, state in sorted(nodes.items()) if state != "passed"]
    results = {}
    for name, entry in deployments.items():
        if entry["status"] != "supported":
            results[name] = "not yet supported"
            continue
        results[name] = contract_result(entry["contract"], nodes)
        if results[name] != "passed":
            problems.append(f"supported deployment {name}: contract {entry['contract']} {results[name]}")
    return problems, results


def notes(deployments: dict, results: dict) -> str:
    lines = ["## Deployments", ""]
    for name, entry in deployments.items():
        state = "supported, contract passed" if results[name] == "passed" else results[name]
        lines.append(f"- {name} ({entry['revision'][:12]}): {state}. {entry['notes']}")
    return "\n".join(lines) + "\n"


def broad_tags() -> str:
    """The behave tags of the broad suite, as RIGGING.md states them."""
    import re
    line = next(l for l in (ROOT / "RIGGING.md").read_text().splitlines() if l.startswith("- broad:"))
    return re.search(r'--tags="([^"]+)"', line).group(1)


def _state(root: Path) -> tuple:
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    clean = not subprocess.run(["git", "-C", str(root), "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    return head, clean


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--notes", help="write the deployment section here when all checks pass")
    ns = ap.parse_args(argv)
    deployments = tomllib.loads((ROOT / "deployments.toml").read_text())["deployments"]
    before = _state(ROOT)
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "junit.xml"
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rs", f"--junitxml={report}"], cwd=ROOT,
                           env={**os.environ, "PATHFINDER_RELEASE": "1"})
        nodes = node_ids(report) if report.exists() else {}
    b = subprocess.run([sys.executable, "-m", "behave", f"--tags={broad_tags()}", "--format=progress"], cwd=ROOT)
    after = _state(ROOT)
    problems, results = evaluate(nodes, r.returncode, deployments, before, after, behave_returncode=b.returncode)
    text = notes(deployments, results)
    print(text)
    if problems:
        print("RELEASE CHECK FAILED\n" + "\n".join(f"- {p}" for p in problems))
        return 1
    if ns.notes:
        Path(ns.notes).write_text(text)
    print(f"release check passed; tag commit {before[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
