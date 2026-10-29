import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from filter import normalize_link

STATE_PATH = Path(__file__).resolve().parent.parent / "seen.json"
LINK_DAYS = 30
WEEK_DAYS = 8

# Nothing has been posted yet
def empty_state():
    return {"links": {}, "messages": [], "week": []}

# Read seen.json or start fresh
def load_state(path=STATE_PATH):
    state = empty_state()
    try:
        with open(path, encoding="utf-8") as f:
            state.update(json.load(f))
    except FileNotFoundError:
        pass
    return state

# Write seen.json with formatting
def save_state(state, path=STATE_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")

# Drop links older than LINK_DAYS
def prune(state, now=None):
    now = now or datetime.now(timezone.utc)
    link_cutoff = now - timedelta(days=LINK_DAYS)
    week_cutoff = now - timedelta(days=WEEK_DAYS)
    state["links"] = {
        link: stamp for link, stamp in state["links"].items()
        if datetime.fromisoformat(stamp) >= link_cutoff
    }
    state["week"] = [
        p for p in state["week"]
        if datetime.fromisoformat(p["picked"]) >= week_cutoff
    ]

# Remember daily picks (no repeats)
def record_picks(state, picks, now):
    stamp = now.isoformat()
    for item in picks:
        if item["link"]:
            state["links"][normalize_link(item["link"])] = stamp
        published = item.get("published")
        state["week"].append({
            "title": item["title"],
            "link": item["link"],
            "summary": item["summary"],
            "source": item["source"],
            "category": item["category"],
            "color": item["color"],
            "image": item.get("image"),
            "published": published.isoformat() if published else None,
            "score": item.get("score", 0),
            "weight": item.get("weight", 1.0),
            "picked": stamp,
        })