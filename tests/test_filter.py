from datetime import datetime, timedelta, timezone
from filter import dedupe, drop_seen, filter_recent, normalize_link

def hours_ago(hours):
    return datetime.now(timezone.utc) - timedelta(hours=hours)

def test_filter_recent_drops_old_items(make_item):
    fresh = make_item(title="fresh", published=hours_ago(2))
    stale = make_item(title="stale", published=hours_ago(30))
    assert filter_recent([fresh, stale], max_age_hours=24) == [fresh]

def test_filter_recent_drops_items_without_date(make_item):
    undated = make_item(published=None)
    assert filter_recent([undated], max_age_hours=24) == []

def test_normalize_link_strips_tracking_but_keeps_real_params():
    messy = normalize_link("https://www.Example.com/story/?id=5&utm_source=rss&fbclid=abc#top")
    clean = normalize_link("http://example.com/story?id=5")
    assert messy == clean

def test_dedupe_matches_links_with_tracking_params(make_item):
    a = make_item(title="A", link="https://example.com/story?utm_source=rss")
    b = make_item(title="B", link="https://www.example.com/story/")
    assert len(dedupe([a, b])) == 1

def test_dedupe_matches_titles_ignoring_case_and_spacing(make_item):
    a = make_item(title="Big News Today", link="https://a.com/1")
    b = make_item(title=" big news  today", link="https://b.com/2")
    assert len(dedupe([a, b])) == 1

def test_dedupe_keeps_copy_from_higher_weight_source(make_item):
    low = make_item(source="Low", weight=0.5)
    high = make_item(source="High", weight=1.0)
    assert [i["source"] for i in dedupe([low, high])] == ["High"]

def test_dedupe_keeps_different_stories(make_item):
    a = make_item(title="One", link="https://a.com/1")
    b = make_item(title="Two", link="https://a.com/2")
    assert len(dedupe([a, b])) == 2

def test_drop_seen_removes_previously_posted_links(make_item):
    posted = make_item(link="https://example.com/story?utm_source=rss")
    fresh = make_item(link="https://example.com/other")
    seen = {normalize_link("https://www.example.com/story/"): "2026-10-11T11:37:00+00:00"}
    assert drop_seen([posted, fresh], seen) == [fresh]