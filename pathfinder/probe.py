"""Vera probe (D10, second half): does the reviewer notice a planted flaw?

    pathfinder --root SOURCE probe-vera --pairs Q1P1 Q2P2 --out DIR

For each finished pair of a source campaign, DIR gets two copies of its thread: one as it is, and one where a
single number in one substantive finding is changed (the flaw is planted in the last finding that has a
number of two or more significant digits; the rest of the ledger is untouched, so later entries that rely on
the right value now disagree with it). Each copy then gets one direct-EVA ledger review and nothing else. A
review "detects" when it issues a request; a request on a sound copy is a false alarm. probe-report.json
records each unit, the planted change, the requests and whether one of them names the changed value."""
from __future__ import annotations
import json, re, shutil
from pathlib import Path
from . import config, research
from .ledger import SUBSTANTIVE

NUMBER = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.]*\d)")


def plant(text: str) -> tuple[str, dict]:
    """The text with its first number of two or more significant digits changed (multiplied by 3), and the change."""
    for m in NUMBER.finditer(text):
        token = m.group(1)
        digits = token.replace(".", "").lstrip("0")
        if len(digits) < 2:
            continue
        value = float(token) * 3
        after = (f"{value:.{len(token.split('.')[1])}f}" if "." in token else str(int(value)))
        return text[:m.start(1)] + after + text[m.end(1):], {"before": token, "after": after}
    raise ValueError("no number to change")


def _flaw(ledger: Path) -> dict:
    rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    for row in reversed(rows):
        if row.get("kind") in SUBSTANTIVE:
            try:
                row["text"], change = plant(row["text"])
            except ValueError:
                continue
            ledger.write_text("".join(json.dumps(r) + "\n" for r in rows))
            return {**change, "seq": row["seq"]}
    raise ValueError(f"{ledger}: no finding with a number to change")


def run(source, pairs: list[str], out: Path) -> dict:
    out = Path(out)
    if out.exists():
        raise SystemExit(f"{out} exists: a probe is built once")
    (out / "threads").mkdir(parents=True)
    raw = {**source.raw, "research_scheme": "direct_eva", "imported_research": True, "ledger_reviews": 1, "rounds": 0}
    for key in ("research_bundles", "branches", "branch", "joint", "parent"):
        raw.pop(key, None)
    (out / "campaign.json").write_text(json.dumps(raw, indent=1))
    Q, P, units, shortlist = [], [], {}, []
    for pair in pairs:
        q, p = research._pair(source, pair)
        for variant in ("sound", "flawed"):
            n = len(Q) + 1
            Q.append(q); P.append(p)
            probe_pair = f"Q{n}P{n}"
            src, dst = source.thread_dir(pair), out / "threads" / probe_pair
            dst.mkdir()
            shutil.copytree(src / "inputs", dst / "inputs")
            for name in ("ledger.jsonl", "external-references.json"):
                if (src / name).exists():
                    shutil.copy2(src / name, dst / name)
            for actor in source.peers:
                if (src / actor).is_dir():
                    shutil.copytree(src / actor, dst / actor)
            units[f"{pair}-{variant}"] = {"pair": probe_pair, "source": pair, "variant": variant,
                                          "planted": _flaw(dst / "ledger.jsonl") if variant == "flawed" else None}
            shortlist.append({"pair_id": probe_pair})
    for name, rows in (("Q.jsonl", Q), ("P.jsonl", P)):
        (out / name).write_text("".join(json.dumps({k: v for k, v in r.items() if k != "text"}) + "\n" for r in rows))
    (out / "shortlist.json").write_text(json.dumps({"pairs": shortlist}))
    campaign = config.load(out)
    for name, unit in units.items():
        pair = unit["pair"]
        research._set(campaign, pair, round=0, stage="ledger_review", status="running", reason=None, started=research._now())
        research.run_thread(campaign, pair)
        s = research.status(campaign, pair)
        requests = [r for r in (s.get("requests") or {}).values()]
        texts = " ".join(str(r.get("text", "")) for r in requests)
        unit.update(status=s.get("status"), reason=s.get("reason"), requests=len(requests),
                    names_the_change=bool(unit["planted"]) and unit["planted"]["after"] in texts)
    flawed = [u for u in units.values() if u["variant"] == "flawed" and u.get("status") not in ("BLOCKED", "stopped")]
    sound = [u for u in units.values() if u["variant"] == "sound" and u.get("status") not in ("BLOCKED", "stopped")]
    report = {"units": units,
              "detection_rate": round(sum(u["requests"] > 0 for u in flawed) / len(flawed), 3) if flawed else None,
              "named_rate": round(sum(u["names_the_change"] for u in flawed) / len(flawed), 3) if flawed else None,
              "false_alarm_rate": round(sum(u["requests"] > 0 for u in sound) / len(sound), 3) if sound else None}
    (out / "probe-report.json").write_text(json.dumps(report, indent=1))
    return report
