from datetime import datetime, timezone
import pytest

# Factory for fake feed items
@pytest.fixture
def make_item():
    def _make(**overrides):
        item = {
            "title": "Some headline",
            "link": "https://example.com/story",
            "summary": "",
            "published": datetime.now(timezone.utc),
            "source": "Test source",
            "category": "tech",
            "weight": 1.0,
        }
        item.update(overrides)
        return item
    return _make