import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import yaml
from fetch import fetch_feed
from post import send

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
OLDEST = datetime.min.replace(tzinfo=timezone.utc)

# Read config.yaml from repo root and return as a dict
def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)

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
            items.append(item)
    return items, failed

# Rate how good an item is; its source weight + the weight of every keyword that appears in its title or summary
def score(item, keywords):
    text = f"{item['title']} {item['summary']}".lower()
    bonus = sum(w for kw, w in keywords.items() if kw.lower() in text)
    return item["weight"] + bonus

""" 
Choose the single best item for each category, in config order
Only items newer than max_age_hours are considered
If a category has none, all of its items are used instead
Categories with no items are skipped
"""
def pick_one_per_category(items, categories, keywords, max_age_hours):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    picks = []
    for category in categories:
        in_cat = [i for i in items if i["category"] == category]
        recent = [i for i in in_cat if i["published"] and i["published"] >= cutoff]
        pool = recent or in_cat
        if not pool:
            print(f"No items found for {category}")
            continue
        best = max(pool, key=lambda i: (score(i, keywords), i["published"] or OLDEST))
        picks.append(best)
    return picks
 
# Turn one feed into Discord embed dict
# Category label shows above the title and the source name in the footer
def build_embed(item, label):
    embed = {
        "author": {"name": label},
        "title": item["title"][:256], # Discord title limit
        "url": item["link"],
        "footer": {"text": item["source"]},
    }

    if item["summary"]:
        embed["description"] = item["summary"]
    if item["published"]:
        embed["timestamp"] = item["published"].isoformat()
    return embed

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
    picks = pick_one_per_category(items, categories, keywords,
                                  config.get("max_age_hours", 24))
    embeds = [build_embed(i, categories[i["category"]]) for i in picks]

    today = datetime.now().strftime("%a %b %d")
    content = f"Daily Digest · {today}"
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