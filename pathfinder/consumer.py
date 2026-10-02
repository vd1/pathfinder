"""The post-edit consumer stage (H9): a deployment's own step after a pair is edited, such as statarb's
implementation of a strategy from the readable note. It runs once per edit, its outcome is recorded in
consumer.json beside the thread, and it cannot overturn the verifier: the research and edit status files
are restored if the consumer changed them, and the record says so. A consumer that raises is recorded as
failed; nothing propagates into the pipeline."""
from __future__ import annotations
import json, time, traceback
from . import extensions


def run(campaign, pair_id: str) -> str:
    try:
        fn = extensions.load(campaign, "consumer")
    except Exception as error:                      # a misconfigured consumer is recorded, never raised into the edit
        fn, problem = None, f"configuration: {type(error).__name__}: {error}"
    else:
        problem = None
        if fn is None:
            return "skipped"
    d = campaign.thread_dir(pair_id)
    guarded = [d / "status.json", d / "edited" / "edit.json"]
    before = {p: p.read_bytes() if p.exists() else None for p in guarded}
    record = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "status": "done", "result": None, "error": None,
              "overturn_refused": False}
    try:
        if problem:
            record.update(status="failed", error=problem)
        else:
            record["result"] = fn(campaign, pair_id, d / "edited")
    except Exception as error:                      # a deployment's failure is its own, recorded, never raised
        record.update(status="failed", error=f"{type(error).__name__}: {error}",
                      traceback=traceback.format_exc(limit=5))
    finally:                                        # even on an interrupt, the verifier's word stands
        for path, data in before.items():
            now = path.read_bytes() if path.exists() else None
            if now != data:
                record["overturn_refused"] = True
                if data is None:
                    path.unlink()
                else:
                    path.write_bytes(data)
    try:
        json.dumps(record["result"])
    except (TypeError, ValueError):
        record["result"] = repr(record["result"])
    (d / "consumer.json").write_text(json.dumps(record, indent=1))
    return record["status"]
