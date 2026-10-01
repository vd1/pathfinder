"""Fake claude/codex binary. Env FAKE_MODE: claude|codex. FAKE_REPLY: text to return.
FAKE_DELAY: seconds before the session line. FAKE_HANG=1: never print a session line.
FAKE_RUN: a shell command to run (in cwd) before replying, so tests can make it write files.
FAKE_USAGE: JSON replacing the final usage object; "null" leaves usage out. FAKE_PARTIAL=1 (claude):
report one turn's usage before FAKE_RUN, so a killed call has partial usage. FAKE_FAIL: codex only, emit
turn.failed with this message and exit 1. FAKE_TOOLS: number of tool uses to emit before the reply."""
import json, os, subprocess, sys, time
mode, reply = os.environ.get("FAKE_MODE", "claude"), os.environ.get("FAKE_REPLY", "ok")
sys.stdin.read()
if os.environ.get("FAKE_HANG"):
    time.sleep(3600)
time.sleep(float(os.environ.get("FAKE_DELAY", "0")))
if mode == "claude":
    print(json.dumps({"type": "system", "subtype": "init", "session_id": "fake-session"}), flush=True)
else:
    print(json.dumps({"type": "thread.started", "thread_id": "fake-thread"}), flush=True)
if mode != "claude" and os.environ.get("FAKE_FAIL"):
    print(json.dumps({"type": "turn.failed", "error": {"message": os.environ["FAKE_FAIL"]}}), flush=True)
    sys.exit(1)
for i in range(int(os.environ.get("FAKE_TOOLS", "0"))):
    failed = i < int(os.environ.get("FAKE_TOOL_FAIL", "0"))     # FAKE_TOOL_FAIL: how many of them fail
    if mode == "claude":
        print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}}))
        if failed:
            print(json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "is_error": True,
                                                                         "content": "No module named pathfinder.ledger"}]}}))
    else:
        print(json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": f"cmd {i}",
                          "exit_code": 1 if failed else 0,
                          "aggregated_output": "No module named pathfinder.ledger" if failed else "ok"}}))
final = json.loads(os.environ["FAKE_USAGE"]) if "FAKE_USAGE" in os.environ else "default"
if os.environ.get("FAKE_PARTIAL"):
    print(json.dumps({"type": "assistant", "message": {"usage": {"input_tokens": 4, "output_tokens": 1}}}), flush=True)
if os.environ.get("FAKE_RUN"):
    subprocess.run(os.environ["FAKE_RUN"], shell=True, check=True)
if mode == "claude":
    print(json.dumps({"type": "assistant", "message": {"usage": {"input_tokens": 1, "cache_creation_input_tokens": 5, "cache_read_input_tokens": 2}}}))
    is_error = bool(os.environ.get("FAKE_ERROR"))
    print(json.dumps({"type": "result", "subtype": "success", "result": reply, "session_id": "fake-session", "is_error": is_error,
                       **({"total_cost_usd": 0.5} if final == "default" else {}),
                       "usage": {"input_tokens": 100, "output_tokens": 10, "cache_creation_input_tokens": 7, "cache_read_input_tokens": 3} if final == "default" else final}))
else:
    print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": reply}}))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 10} if final == "default" else final}))
