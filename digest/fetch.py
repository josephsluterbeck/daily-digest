import feedparser
import html, re
from datetime import datetime, timezone

# Browser-like User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)

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

# Find a thumbnail image URL for an entry if provided
# Return None otherwise
def _image(entry):
    for m in entry.get("media_thumbnail", []):
        if m.get("url"):
            return m["url"]
        for m in entry.get("media_content", []):
            if m.get("url") and (m.get("medium") == "image" or str(m.get("type", "")).startswith("image")):
                return m["url"]
        for link in entry.get("links", []):
            if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("image"):
                return link.get("href")
        return None

# Fetch one RSS/Atom feed and return list of item dicts
def fetch_feed(url, agent=USER_AGENT):
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
            "image": _image(entry),
        })
    return items