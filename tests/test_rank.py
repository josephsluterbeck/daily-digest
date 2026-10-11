from datetime import datetime, timedelta, timezone
from rank import pick_top, score

CATEGORIES = {"world": "World News", "tech": "Tech / CS"}

def test_title_hit_counts_double_summary_hit(make_item):
    keywords = {"python": 1}
    in_title = make_item(title="Python 4 released")
    in_summary = make_item(title="New release", summary="The python team shipped it")
    assert score(in_title, keywords) == 2
    assert score(in_summary, keywords) == 1

def test_score_is_multiplied_by_source_weight(make_item):
    item = make_item(title="Python news", weight=0.5)
    assert score(item, {"python": 1}) == 1.0

def test_keywords_match_whole_words_only(make_item):
    item = make_item(title="Official said nothing")
    assert score(item, {"ai": 1}) == 0

def test_pick_top_returns_one_per_category_in_config_order(make_item):
    items = [
        make_item(title="Tech story", category="tech"),
        make_item(title="World story", category="world"),
    ]
    picks = pick_top(items, CATEGORIES, {}, max_items=7)
    assert[p["category"] for p in picks] == ["world", "tech"]

def test_pick_top_prefers_keyword_match(make_item):
    plain = make_item(title="Generic update")
    match = make_item(title="CUDA 13 announced")
    assert pick_top([plain, match], CATEGORIES, {"cuda": 2}, max_items=7) == [match]

def test_pick_top_breaks_ties_by_weight_then_newest(make_item):
    now = datetime.now(timezone.utc)
    low_new = make_item(title="a", weight=0.5, published=now)
    high_old = make_item(title="b", weight=1.0, published=now - timedelta(hours=5))
    high_new = make_item(title="c", weight=1.0, published=now - timedelta(hours=1))
    picks = pick_top([low_new, high_old, high_new], CATEGORIES, {}, max_items=7)
    assert picks == [high_new]

def test_pick_top_skips_empty_categories_and_respects_max(make_item):
    items = [make_item(category="tech")]
    assert len(pick_top(items, CATEGORIES, {}, max_items=7)) == 1
    assert pick_top(items, CATEGORIES, {}, max_items=0) == []