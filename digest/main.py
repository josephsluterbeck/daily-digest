import argparse
import json
from datetime import datetime, timezone
from fetch import fetch_feed
from post import send

FEED_URL = "https://hnrss.org/frontpage"
MAX_ITEMS = 5
OLDEST = datetime.min.replace(tzinfo=timezone.utc)

# Turn one feed into Discord embed dict
def build_embed(item):
    embed = {
        "title": item["title"][:256], # Discord title limit
        "url": item["link"],
        "footer": {"text": item["source"]},
    }

    if item["summary"]:
        embed["description"] = item["summary"]
    if item["published"]:
        embed["timestamp"] = item["published"].isoformat()
    return embed

def main():
    parser = argparse.ArgumentParser(description="Post the daily digest to Discord.")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the embeds instead of sending them")
    args = parser.parse_args()

    items = fetch_feed(FEED_URL)
    items.sort(key=lambda i: i["published"] or OLDEST, reverse=True)
    embeds = [build_embed(i) for i in items[:MAX_ITEMS]]

    if args.dry_run:
        print(json.dumps(embeds, indent=2, ensure_ascii=False))
        return

    send("Daily Digest", embeds)
    print(f"Sent {len(embeds)} items.")

if __name__ == "__main__":
    main()