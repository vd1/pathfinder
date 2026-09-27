import pytest

from pathfinder import alerts


@pytest.fixture(autouse=True)
def no_real_desktop_notifications(monkeypatch):
    """Failure tests must not notify the user's desktop."""
    monkeypatch.setattr(alerts, "_desktop", lambda *args: "test-suppressed")
