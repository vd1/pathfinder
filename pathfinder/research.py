"""One research thread: peers on a shared ledger, consolidate, verify, up to `rounds` rounds."""
from __future__ import annotations
import hashlib, json, shutil, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import corpus, transport
from .ledger import Ledger
from .scan import prompts_dir, parse_json

PEERS = ("ada", "emmy")                      # the default; a campaign may name more in campaign.json
TERMINAL = {"DRAFT", "PAUSE", "PAUSE-ON-ITERATE", "PAUSE-ON-REVISE"}


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
    for a in campaign.peers:
        (d / a).mkdir(exist_ok=True)
    _set(campaign, pair_id, round=1, stage="peers", status="running", reason=None, started=_now())
    return d


def thread_head(d, inp) -> str:
    """The static head of every call in a thread: the two papers, then the ledger as it stands.
    The same bytes for every researcher, the consolidator and both judges, and across calls a prefix
    of the previous call's, since the ledger only grows; a prompt cache serves everything but what the
    ledger gained since. Whatever differs between callers goes after it."""
    h = "## " + inp["Q"] + "\n\n" + (d / "inputs" / inp["Q"]).read_text(errors="replace")
    h += "\n\n## " + inp["P"] + "\n\n" + (d / "inputs" / inp["P"]).read_text(errors="replace")
    h += "\n\n## ledger.jsonl\n\n" + ((d / "ledger.jsonl").read_text() if (d / "ledger.jsonl").exists() else "")
    return h


def judge_head(d, inp, note_name: str) -> str:
    """The thread head plus the note, for the verifier and the paper reviewer."""
    return thread_head(d, inp) + "\n\n## " + note_name + "\n\n" + (d / note_name).read_text(errors="replace")


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


def _scan_row(campaign, pair_id) -> dict:
    p = campaign.path("scan.jsonl")
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip() and json.loads(line).get("pair_id") == pair_id:
                return json.loads(line)
    return {}


def _peers(campaign, pair_id, stop):
    d, L = campaign.thread_dir(pair_id), Ledger(campaign.thread_dir(pair_id) / "ledger.jsonl")
    A = campaign.allowances; inp = _inputs(d); row = _scan_row(campaign, pair_id)
    helper = f"{sys.executable} -m pathfinder.ledger --root ."
    used = {"seconds": 0.0}; lock = threading.Lock()

    peers = list(campaign.peers)

    def one(actor):
        others = [a for a in peers if a != actor]
        for call_no in range(A["peer_calls"]):
            with lock:
                left = A["peer_seconds"] - used["seconds"]
            if left <= 0 or L.ready(peers):
                return
            while L.ready([actor]) and not all(done[o] for o in others):   # my word stands; wait for my partners
                time.sleep(15)
                if L.ready(peers):
                    return
            if L.ready(peers):
                return
            _check(stop)
            p = thread_head(d, inp) + "\n\n## your task\n\n"
            p += _prompt(campaign, "peer", ACTOR=actor, PEERS=" and ".join(others), Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}",
                        LEDGER=f"{helper} --actor {actor}", SECONDS=int(min(left, 1200)),
                        CALLS_LEFT=A["peer_calls"] - call_no - 1, FEASIBILITY=row.get("feasibility", "?"),
                        GAIN=row.get("gain", "?"), CONNEXION=row.get("connexion") or "none recorded.",
                        RATIONALE=row.get("rationale") or "none recorded.")
            if call_no or L.count():
                p += "\n\nThis call continues an existing thread. Start by reading the ledger, then carry on from where it stands.\n"
            r = transport.call(p, campaign=campaign, model=campaign.model, tools=True, search=campaign.peer_search,
                               cwd=d, timeout=int(min(left, 1200)) + 30, thread=pair_id, stage="peers", actor=actor)
            with lock:
                used["seconds"] += r["seconds"]
            if r["transport_failed"]:
                raise transport.TransportFailed(pair_id)

    done = {a: False for a in peers}

    def guarded(actor):
        try:
            one(actor)
        finally:
            done[actor] = True

    with ThreadPoolExecutor(len(peers)) as ex:
        for f in [ex.submit(guarded, a) for a in peers]:
            f.result()


def _stage_call(campaign, pair_id, stage, prompt, tools, seconds, done=lambda: False):
    """Run consolidate or verify; rerun once on timeout or empty reply unless done() says the output exists."""
    d = campaign.thread_dir(pair_id)
    for attempt in range(2):
        r = transport.call(prompt, campaign=campaign, model=campaign.model, tools=tools, search=False, cwd=d,
                           timeout=seconds, thread=pair_id, stage=stage, actor=campaign.peers[0] if stage == "consolidate" else "verifier")
        if r["transport_failed"]:
            raise transport.TransportFailed(pair_id)
        if r["text"] or r["error"] is None or done():
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
                why = "" if L.ready(list(campaign.peers)) else " because the allowance ran out before every peer declared ready"
                repair = s.get("repair")
                if repair:
                    prior = (f" This is a repair of the existing {note.name}, not new research. An independent verifier found"
                             f" these defects: {repair.get('reason')} Corrections: {repair.get('action')} Correct them, keep every"
                             " result the verifier accepted, and do not open new directions.")
                elif note.exists():
                    prior = (f" A previous round wrote {note.name} and the verifier returned ITERATE on it; keep every result"
                             " of that note that still stands and append this round's work to it, rather than rewriting from"
                             " scratch. The verifier's review is the latest review entry in the ledger.")
                else:
                    prior = ""
                r = _stage_call(campaign, pair_id, "consolidate",
                                thread_head(d, inp) + "\n\n## your task\n\n"
                                + _prompt(campaign, "consolidate", ACTOR=campaign.peers[0], WHY=why, NOTE=note.name, NOTE_STEM=pair_id, PRIOR=prior), True,
                                A["consolidate_seconds"], done=note.exists)
                if not note.exists():
                    if r["text"].strip():
                        note.write_text(r["text"])
                    else:
                        _set(campaign, pair_id, status="BLOCKED", reason=f"consolidate: {r['error'] or 'no note'}"); return "BLOCKED"
                _set(campaign, pair_id, stage="verify", repair=None)
            elif s["stage"] == "verify":
                _check(stop)
                # static material first, the instruction last: the head is shared with every other judge call
                p = judge_head(d, inp, note.name) + "\n\n## your task\n\n"
                p += _prompt(campaign, "verify", Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}", NOTE=note.name)
                r = _stage_call(campaign, pair_id, "verify", p, False, A["verify_seconds"])
                try:
                    v = parse_json(r["text"]); dec = v["decision"].upper()
                    assert dec in ("DRAFT", "REVISE", "ITERATE", "PAUSE")
                except Exception as e:
                    (d / "verify-unreadable.txt").write_text(r["text"] or "")     # keep the paid reply for inspection
                    _set(campaign, pair_id, status="BLOCKED", reason=f"verify: unreadable decision ({e})"); return "BLOCKED"
                hist = json.loads(verdicts.read_text()) if verdicts.exists() else []
                hist.append({"round": s["round"], "at": _now(), "note_sha256": hashlib.sha256(note.read_bytes()).hexdigest(), **v})
                verdicts.write_text(json.dumps(hist, indent=1))
                repairs = s.get("repairs", 0)
                if dec == "REVISE" and repairs < campaign.raw.get("repairs", 1):
                    L.add("verifier", "review", f"REVISE: {v.get('reason')} Corrections: {v.get('action')}")
                    _set(campaign, pair_id, stage="consolidate", repairs=repairs + 1, repair=v, reason=v.get("reason"))
                elif dec == "ITERATE" and s["round"] < campaign.rounds:
                    L.add("verifier", "review", f"ITERATE: {v.get('reason')} Action: {v.get('action')}")
                    _set(campaign, pair_id, stage="peers", round=s["round"] + 1, reason=v.get("reason"))
                else:
                    final = {"ITERATE": "PAUSE-ON-ITERATE", "REVISE": "PAUSE-ON-REVISE"}.get(dec, dec)
                    _set(campaign, pair_id, stage="done", status=final, reason=v.get("reason")); return final
    except Stopped:
        _set(campaign, pair_id, status="stopped"); return "stopped"
    except transport.TransportFailed:
        _set(campaign, pair_id, status="stopped", reason="transport failed"); raise
