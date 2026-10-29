from datetime import datetime, timedelta, timezone
from state import empty_state, prune

def test_prune_drops_old_links_and_weekly_picks():
    now = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)
    state = empty_state()
    state["links"] = {
        "old": (now - timedelta(days=40)).isoformat(),
        "new": (now - timedelta(days=2)).isoformat(),
    }
    state["week"] = [
        {"picked": (now - timedelta(days=10)).isoformat()},
        {"picked": (now - timedelta(days=1)).isoformat()},
    ]
    prune(state, now)
    assert list(state["links"]) == ["new"]
    assert len(state["week"]) == 1