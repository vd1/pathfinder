"""One research thread: peers on a shared ledger, consolidate, verify, up to `rounds` rounds."""
from __future__ import annotations
import json, shutil, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import corpus, transport
from .ledger import Ledger
from .scan import prompts_dir, parse_json

PEERS = ("ada", "emmy")
TERMINAL = {"DRAFT", "PAUSE", "PAUSE-ON-ITERATE"}


class Stopped(Exception):
    pass


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def status(campaign, pair_id) -> dict:
    p = campaign.thread_dir(pair_id) / "status.json"
    return json.loads(p.read_text()) if p.exists() else {"pair_id": pair_id, "round": 0, "stage": "peers", "status": "new"}


def _set(campaign, pair_id, **kw):
    s = status(campaign, pair_id); s.update(kw, updated=_now())
    (campaign.thread_dir(pair_id) / "status.json").write_text(json.dumps(s, indent=1))
    return s


def _pair(campaign, pair_id):
    i, j = (int(x) for x in pair_id[1:].split("P"))
    return corpus.read(campaign.path("Q.jsonl"))[i - 1], corpus.read(campaign.path("P.jsonl"))[j - 1]


def prepare(campaign, pair_id: str) -> Path:
    d = campaign.thread_dir(pair_id)
    if (d / "status.json").exists():
        return d
    (d / "inputs").mkdir(parents=True, exist_ok=True)
    for side, row in zip("QP", _pair(campaign, pair_id)):
        src = campaign.path(row["text"]) if row.get("text") else None
        if src and src.exists():
            shutil.copy(src, d / "inputs" / f"{side}{src.suffix}")
        else:
            (d / "inputs" / f"{side}.txt").write_text(f"Title: {row['title']}\n\nAbstract: {row['abstract']}\n")
        (d / "inputs" / f"{side}.json").write_text(json.dumps(row, indent=1))
    for a in PEERS:
        (d / a).mkdir(exist_ok=True)
    _set(campaign, pair_id, round=1, stage="peers", status="running", reason=None, started=_now())
    return d


def _inputs(d: Path) -> dict:
    return {s: next(p for p in (d / "inputs").iterdir() if p.stem == s and p.suffix != ".json").name for s in "QP"}


def _prompt(campaign, name, **vars):
    t = (prompts_dir(campaign) / f"{name}.md").read_text()
    for k, v in vars.items():
        t = t.replace("{{" + k + "}}", str(v))
    return t


def _check(stop):
    if stop():
        raise Stopped()


def _peers(campaign, pair_id, stop):
    d, L = campaign.thread_dir(pair_id), Ledger(campaign.thread_dir(pair_id) / "ledger.jsonl")
    A = campaign.allowances; inp = _inputs(d)
    helper = f"{sys.executable} -m pathfinder.ledger --root ."
    used = {"seconds": 0.0}; lock = threading.Lock()

    def one(actor):
        peer = PEERS[1 - PEERS.index(actor)]
        for call_no in range(A["peer_calls"]):
            with lock:
                left = A["peer_seconds"] - used["seconds"]
            if left <= 0 or L.ready(list(PEERS)):
                return
            while L.ready([actor]) and not done[peer]:      # my word stands; wait for my partner
                time.sleep(15)
                if L.ready(list(PEERS)):
                    return
            if L.ready(list(PEERS)):
                return
            _check(stop)
            p = _prompt(campaign, "peer", ACTOR=actor, PEER=peer, Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}",
                        LEDGER=f"{helper} --actor {actor}", SECONDS=int(min(left, 1200)),
                        CALLS_LEFT=A["peer_calls"] - call_no - 1)
            if call_no or L.count():
                p += "\n\nThis is a resumed call on the same thread. Read the ledger first; do not repeat work.\n"
            r = transport.call(p, campaign=campaign, model=campaign.model, tools=True, search=campaign.peer_search,
                               cwd=d, timeout=int(min(left, 1200)) + 30, thread=pair_id, stage="peers", actor=actor)
            with lock:
                used["seconds"] += r["seconds"]
            if r["transport_failed"]:
                raise transport.TransportFailed(pair_id)

    done = {a: False for a in PEERS}

    def guarded(actor):
        try:
            one(actor)
        finally:
            done[actor] = True

    with ThreadPoolExecutor(2) as ex:
        for f in [ex.submit(guarded, a) for a in PEERS]:
            f.result()


def _stage_call(campaign, pair_id, stage, prompt, tools, seconds):
    """Run consolidate or verify; rerun once on timeout or empty reply."""
    d = campaign.thread_dir(pair_id)
    for attempt in range(2):
        r = transport.call(prompt, campaign=campaign, model=campaign.model, tools=tools, search=False, cwd=d,
                           timeout=seconds, thread=pair_id, stage=stage, actor="ada" if stage == "consolidate" else "verifier")
        if r["transport_failed"]:
            raise transport.TransportFailed(pair_id)
        if r["text"] or r["error"] is None:
            return r
    return r


def run_thread(campaign, pair_id: str, stop=lambda: False) -> str:
    d = prepare(campaign, pair_id); L = Ledger(d / "ledger.jsonl"); A = campaign.allowances
    note, verdicts = d / f"{pair_id}.tex", d / f"{pair_id}.verdict.json"
    inp = _inputs(d)
    try:
        while True:
            s = status(campaign, pair_id)
            if s["status"] in TERMINAL:
                return s["status"]
            _set(campaign, pair_id, status="running")
            if s["stage"] == "peers":
                _check(stop); _peers(campaign, pair_id, stop)
                if L.latest_substantive() == 0:
                    _set(campaign, pair_id, stage="done", status="PAUSE", reason="empty ledger"); return "PAUSE"
                _set(campaign, pair_id, stage="consolidate")
            elif s["stage"] == "consolidate":
                _check(stop)
                why = "" if L.ready(list(PEERS)) else " because the allowance ran out before both peers declared ready"
                r = _stage_call(campaign, pair_id, "consolidate",
                                _prompt(campaign, "consolidate", ACTOR="ada", WHY=why, NOTE=note.name), True, A["consolidate_seconds"])
                if not note.exists():
                    if r["text"].strip():
                        note.write_text(r["text"])
                    else:
                        _set(campaign, pair_id, status="BLOCKED", reason=f"consolidate: {r['error'] or 'no note'}"); return "BLOCKED"
                _set(campaign, pair_id, stage="verify")
            elif s["stage"] == "verify":
                _check(stop)
                p = _prompt(campaign, "verify", Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}", NOTE=note.name)
                p += "\n\n## " + inp["Q"] + "\n\n" + (d / "inputs" / inp["Q"]).read_text(errors="replace")
                p += "\n\n## " + inp["P"] + "\n\n" + (d / "inputs" / inp["P"]).read_text(errors="replace")
                p += "\n\n## ledger.jsonl\n\n" + (d / "ledger.jsonl").read_text()
                p += "\n\n## " + note.name + "\n\n" + note.read_text(errors="replace")
                r = _stage_call(campaign, pair_id, "verify", p, False, A["verify_seconds"])
                try:
                    v = parse_json(r["text"]); dec = v["decision"].upper()
                    assert dec in ("DRAFT", "ITERATE", "PAUSE")
                except Exception as e:
                    _set(campaign, pair_id, status="BLOCKED", reason=f"verify: unreadable decision ({e})"); return "BLOCKED"
                hist = json.loads(verdicts.read_text()) if verdicts.exists() else []
                hist.append({"round": s["round"], "at": _now(), **v}); verdicts.write_text(json.dumps(hist, indent=1))
                if dec == "ITERATE" and s["round"] < campaign.rounds:
                    L.add("verifier", "review", f"ITERATE: {v.get('reason')} Action: {v.get('action')}")
                    _set(campaign, pair_id, stage="peers", round=s["round"] + 1, reason=v.get("reason"))
                else:
                    final = "PAUSE-ON-ITERATE" if dec == "ITERATE" else dec
                    _set(campaign, pair_id, stage="done", status=final, reason=v.get("reason")); return final
    except Stopped:
        _set(campaign, pair_id, status="stopped"); return "stopped"
    except transport.TransportFailed:
        _set(campaign, pair_id, status="stopped", reason="transport failed"); raise
