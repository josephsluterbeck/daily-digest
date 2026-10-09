import feedparser
import html, re
from datetime import datetime, timezone

# Strip HTML and cut to 200 characters
def _clean(text, limit=200):
    text = re.sub(r"<[^>]+>", "", text or "")  # drop tags
    text = html.unescape(text)  # unescape HTML entities
    text = " ".join(text.split()) # collapse whitespace
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "..."

# Feedparser gives UTC time.struct_time; turn into datetime
def _to_utc(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t:
        return None
    return datetime(*t[:6], tzinfo=timezone.utc)

# Fetch one RSS/Atom feed and return list of item dicts
def fetch_feed(url):
    d = feedparser.parse(url)
    if d.bozo and not d.entries:
        raise RuntimeError(f"Could not fetch feed {url}: {d.get('bozo_exception')}")
    source = d.feed.get("title", url)
    items = []
    for entry in d.entries:
        items.append({
            "title": entry.get("title", "(no title)"),
            "link": entry.get("link", ""),
            "summary": _clean(entry.get("summary", "")),
            "published": _to_utc(entry),
            "source": source,
        })
    return items