"""The release gate: every supported deployment passes against this candidate, and nothing is skipped.

    uv run python scripts/release_check.py [--notes RELEASE_NOTES.md]

Runs the whole test suite with PATHFINDER_RELEASE=1 (so a missing or mispinned deployment checkout fails
instead of skipping), then fails if any test failed, errored or was skipped, if a supported deployment's
contract test did not run, or if the working tree is not clean. Prints the commit to tag and the release
notes' deployment section, which names every deployment the release does not yet support. It never tags."""
import argparse, os, subprocess, sys, tempfile, tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--notes", help="write the deployment section to this file")
    ns = ap.parse_args(argv)
    problems = []
    if subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True).stdout.strip():
        problems.append("the working tree has uncommitted changes")
    deployments = tomllib.loads((ROOT / "deployments.toml").read_text())["deployments"]
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "junit.xml"
        env = {**os.environ, "PATHFINDER_RELEASE": "1"}
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rs", f"--junitxml={report}"], cwd=ROOT, env=env)
        cases = ET.parse(report).getroot().iter("testcase") if report.exists() else []
        ran, skipped, failed = set(), [], []
        for case in cases:
            node = f"{case.get('file') or case.get('classname', '').replace('.', '/') + '.py'}::{case.get('name')}"
            if case.find("skipped") is not None:
                skipped.append(node)
            elif case.find("failure") is not None or case.find("error") is not None:
                failed.append(node)
            else:
                ran.add(node)
    if r.returncode:
        problems.append(f"pytest exited {r.returncode}")
    problems += [f"skipped in a release run: {n}" for n in skipped]
    problems += [f"failed: {n}" for n in failed]
    for name, entry in deployments.items():
        if entry["status"] != "supported":
            continue
        target = entry["contract"].split("::")
        hit = [n for n in ran if n.endswith(target[-1]) or (len(target) == 1 and Path(target[0]).stem in n)]
        if not hit:
            problems.append(f"supported deployment {name}: its contract {entry['contract']} did not pass")
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    notes = ["## Deployments", ""]
    for name, entry in deployments.items():
        state = "supported, contract passed" if entry["status"] == "supported" else "not yet supported"
        notes.append(f"- {name} ({entry['revision'][:12]}): {state}. {entry['notes']}")
    text = "\n".join(notes) + "\n"
    if ns.notes:
        Path(ns.notes).write_text(text)
    print(text)
    if problems:
        print("RELEASE CHECK FAILED\n" + "\n".join(f"- {p}" for p in problems))
        return 1
    print(f"release check passed; tag commit {commit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
