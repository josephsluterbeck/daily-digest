import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import yaml
from fetch import fetch_feed
from filter import dedupe, filter_recent
from post import fit_to_limits, send
from rank import pick_top
from summarize import summarize_item

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

DEFAULT_COLOR = 0x5865F2

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
        for item in entries:
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
    if item["published"]:
        embed["timestamp"] = item["published"].isoformat()
    if item.get("image"):
        embed["thumbnail"] = {"url": item["image"]}
    return embed

# Build the message text above the embeds
def build_header(count, failed, methods):
    now = datetime.now()
    date = f"{now:%A}, {now:%B}, {now.day}"

    if count == 0:
        lines = [f"Daily Digest · {date}",
                 "Nothing new today. Check back tomorrow."]
    else:
        noun = "story" if count == 1 else "stories"
        lines = [f"Daily Digest · {date} · {count} · {noun}"]
        if "ai" not in methods:
            lines.append("AI summaries unavailable today. Check the log.")
    if failed:
        lines.append(f"Failed to load: {', '.join(failed)}")
    return "\n".join(lines)

# Entry point; fetch all feeds, pick one article per category and send to Discord
def main():
    parser = argparse.ArgumentParser(description="Post the daily digest to Discord.")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the embeds instead of sending them")
    args = parser.parse_args()

    config = load_config()
    categories = config["categories"]
    keywords = config.get("keywords") or {}

    items, failed = collect_items(config["sources"])
    items = filter_recent(items, config.get("max_age_hours", 24))
    items = dedupe(items)
    picks = pick_top(items, categories, keywords, config.get("max_items", 7))

    summary_cfg = config.get("summary") or {}
    methods = [summarize_item(item,
                              summary_cfg.get("model", "gemini-3.1-flash-lite"),
                              summary_cfg.get("max_chars", 400))
                              for item in picks]

    embeds = fit_to_limits([build_embed(i, categories[i["category"]]) for i in picks])
    content = build_header(len(embeds), failed, methods)

    today = datetime.now().strftime("%a %b %d")
    if failed:
        content += f"\n Failed to load: {', '.join(failed)}"

    if args.dry_run:
        print(content)
        print(json.dumps(embeds, indent=2, ensure_ascii=False))
        return

    send(content, embeds)
    print(f"Sent {len(embeds)} items.")

if __name__ == "__main__":
    main()