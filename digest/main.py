import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
import yaml
from fetch import fetch_feed
from filter import dedupe, filter_recent, drop_seen
from post import fit_to_limits, send, delete_message
from rank import pick_top, score
from state import load_state, prune, record_picks, save_state
from summarize import summarize_item

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

DEFAULT_COLOR = 0x5865F2

WEEKLY_DAY = 6

# Read config.yaml from repo root and return as a dict
def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)

# Turn a RRGGBB string from the config into the int for Discord
def parse_color(value):
    if not value:
        return DEFAULT_COLOR
    try:
        return int(str(value).lstrip("#"), 16)
    except ValueError:
        print(f"Invalid color {value!r}, using default")
        return DEFAULT_COLOR

# Fetch every source; tag each with its source, category, and weight
# Returns (items, failed): all items tagged with their source name, catgeory, and weight
def collect_items(sources):
    items = []
    failed = []
    for source in sources:
        try:
            entries = fetch_feed(source["url"])
        except Exception as e:
            print(f"Skipping {source['name']}: {e}")
            failed.append(source["name"])
            continue

        exclude = source.get("exclude") or []
        for item in entries:
            if any(re.search(rf"\b{re.escape(word)}\b", item["title"], re.IGNORECASE)
                   for word in exclude):
                continue
            item["source"] = source["name"]
            item["category"] = source["category"]
            item["weight"] = source.get("weight", 1.0)
            item["color"] = parse_color(source.get("color"))
            items.append(item)
    return items, failed
 
# Turn one feed into Discord embed dict
# Category label shows above the title and the source name in the footer
def build_embed(item, label):
    embed = {
        "author": {"name": label},
        "title": item["title"][:256], # Discord title limit
        "url": item["link"],
        "color": item["color"],
        "footer": {"text": item["source"]},
    }

    if item["summary"]:
        embed["description"] = item["summary"]
    published = item.get("published")
    if isinstance(published, str):
        published = datetime.fromisoformat(published)
    if published:
        embed["timestamp"] = published.isoformat()
    if item.get("image"):
        embed["thumbnail"] = {"url": item["image"]}
    return embed

# Build the message text above the embeds
def build_header(count, failed, methods):
    now = datetime.now()
    date = f"{now:%A}, {now:%B} {now.day}"

    if count == 0:
        lines = [f"Daily Digest · {date}",
                 "Nothing new today. Check back tomorrow."]
    else:
        noun = "story" if count == 1 else "stories"
        lines = [f"Daily Digest · {date} · {count} {noun}"]
        if "ai" not in methods:
            lines.append("AI summaries unavailable today. Check the log.")
    if failed:
        lines.append(f"Failed to load: {', '.join(failed)}")
    return "\n".join(lines)

# Week in review: highest-scoring daily pick per category from the last 7 days
def build_weekly(state, categories, now):
    cutoff = now - timedelta(days=7)
    week = [p for p in state["week"] if datetime.fromisoformat(p["picked"]) > cutoff]

    picks = []
    for category in categories:
        pool = [p for p in week if p["category"] == category]
        if pool:
            picks.append(max(pool, key=lambda p: (p["score"], p["weight"], p["picked"])))

    embeds = fit_to_limits([build_embed(p, categories[p["category"]]) for p in picks])
    start = now - timedelta(days=6)
    noun = "story" if len(embeds) == 1 else "stories"
    content = (f"Week in Review · {start:%b} {start.day} - {now:%b} {now.day}"
               f" · {len(embeds)} {noun}")
    return content, embeds

# Delete messages posted 7 max_age_days or more calendar days ago
def cleanup_old_messages(state, max_age_days, now):
    keep = []
    for msg in state["messages"]:
        posted = datetime.fromisoformat(msg["posted"])
        if (now.date() - posted.date()).days < max_age_days:
            keep.append(msg)
            continue
        try:
            delete_message(msg["id"])
            print(f"Deleted message from {posted:%b} {posted.day}")
        except Exception as e:
            print(f"Couldn't delete message {msg['id']}: {e}")
            keep.append(msg)
    state["messages"] = keep

# Entry point; fetch all feeds, pick one article per category and send to Discord
def main():
    parser = argparse.ArgumentParser(description="Post the daily digest to Discord.")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the embeds instead of sending them")
    parser.add_argument("--weekly", action="store_true",
                        help="also build the weekly digest, whatever the day")
    args = parser.parse_args()

    config = load_config()
    categories = config["categories"]
    keywords = config.get("keywords") or {}
    summary_cfg = config.get("summary") or {}

    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    state = load_state()
    prune(state, now)

    if (os.environ.get("GITHUB_EVENT_NAME") == "schedule"
            and state.get("last_posted") == today
            and not args.dry_run):
        print("Already posted today; skipping this scheduled run.")
        return

    items, failed = collect_items(config["sources"])
    items = filter_recent(items, config.get("max_age_hours", 24))
    items = drop_seen(items, state["links"])
    items = dedupe(items)
    picks = pick_top(items, categories, keywords, config.get("max_items", 7))

    methods = [summarize_item(item,
                              summary_cfg.get("model", "gemini-3.1-flash-lite"),
                              summary_cfg.get("max_chars", 400))
                for item in picks]
    for item in picks:
        item["score"] = score(item, keywords)

    embeds = fit_to_limits([build_embed(i, categories[i["category"]]) for i in picks])
    content = build_header(len(embeds), failed, methods)

    record_picks(state, picks, now)
    weekly = None
    if args.weekly or now.weekday() == WEEKLY_DAY:
        weekly = build_weekly(state, categories, now)

    if args.dry_run:
        print(content)
        print(json.dumps(embeds, indent=2, ensure_ascii=False))
        if weekly:
            print("\n" + weekly[0])
            print(json.dumps(weekly[1], indent=2, ensure_ascii=False))
        return

    cleanup_old_messages(state, config.get("delete_after_days", 7), now)

    message_id = send(content, embeds)
    state["messages"].append({"id": message_id, "posted": now.isoformat()})
    state["last_posted"] = today
    print(f"Sent {len(embeds)} items.")

    if weekly and weekly[1]:
        weekly_id = send(*weekly)
        state["messages"].append({"id": weekly_id, "posted": now.isoformat()})
        print(f"Sent weekly digest with {len(weekly[1])} items.")

    if os.environ.get("GITHUB_ACTIONS") == "true":
        save_state(state)
    else:
        print("Local run: seen.json left unchanged.")

if __name__ == "__main__":
    main()