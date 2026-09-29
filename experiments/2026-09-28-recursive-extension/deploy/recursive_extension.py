"""Small deployment policies; the pinned engine remains unchanged."""
import json
import time


def admit(campaign, stage, role, reserved_now):
    from pathfinder import admission, runner
    parent = campaign.root.parent
    launch = parent / "launch.json"
    if not launch.exists():
        return admission.stop("No recorded launch authorization window")
    record = json.loads(launch.read_text())
    if time.time() >= record["admission_deadline"]:
        from types import SimpleNamespace
        owner = SimpleNamespace(path=lambda name: parent / name)
        runner.request_stop(owner, "Authorized admission window ended; drain and hand off")
        return admission.stop("Authorized admission window ended")
    return admission.budget_per_call(campaign, stage, role, reserved_now)


def snapshot(campaign, base):
    from pathfinder import coordinator
    return coordinator.snapshot(campaign.path("schedule.json"))
