import pytest

from pathfinder import alerts


@pytest.fixture(autouse=True)
def no_real_desktop_notifications(monkeypatch):
    """Failure tests must not notify the user's desktop."""
    monkeypatch.setattr(alerts, "_desktop", lambda *args: "test-suppressed")


@pytest.fixture(autouse=True)
def private_accounts(tmp_path_factory, monkeypatch):
    """Seat pools and subscription pauses live under $PATHFINDER_ACCOUNTS: never the user's own."""
    monkeypatch.setenv("PATHFINDER_ACCOUNTS", str(tmp_path_factory.mktemp("accounts")))


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No test downloads a paper: the source service answers from its cache only (pathfinder.paper_source)."""
    monkeypatch.setenv("PATHFINDER_OFFLINE", "1")


@pytest.fixture(autouse=True)
def private_paper_pool(tmp_path, monkeypatch):
    """Tests never read or populate the user's shared paper pool."""
    monkeypatch.setenv("PATHFINDER_SOURCE_CACHE", str(tmp_path / "paper-pool"))
