"""Fake claude/codex binary. Env FAKE_MODE: claude|codex. FAKE_REPLY: text to return.
FAKE_DELAY: seconds before the session line. FAKE_HANG=1: never print a session line.
FAKE_RUN: a shell command to run (in cwd) before replying, so tests can make it write files."""
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
if os.environ.get("FAKE_RUN"):
    subprocess.run(os.environ["FAKE_RUN"], shell=True, check=True)
if mode == "claude":
    print(json.dumps({"type": "assistant", "message": {"usage": {"input_tokens": 1, "cache_creation_input_tokens": 5, "cache_read_input_tokens": 2}}}))
    print(json.dumps({"type": "result", "subtype": "success", "result": reply, "session_id": "fake-session",
                      "total_cost_usd": 0.5, "usage": {"input_tokens": 100, "output_tokens": 10, "cache_creation_input_tokens": 7, "cache_read_input_tokens": 3}}))
else:
    print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": reply}}))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 10}}))
