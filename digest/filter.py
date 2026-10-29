from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Query params that only track clicks and don't change which article a link points to
TRACKING_PARAMS = {
    "fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid",
    "ref", "ref_src", "cmpid", "smid",
}

# Keep only items published within the last max_age_hours
# Items with no date are dropped
def filter_recent(items, max_age_hours=24):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    return [i for i in items if i["published"] and i["published"] >= cutoff]

# Reduce a URL to a comparison key, only used for comparing links
def normalize_link(url):
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    query = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS
    ]
    path = parts.path.rstrip("/")
    return urlunsplit(("https", host, path, urlencode(sorted(query)), ""))

# Lowercase a title and collapse its whitespace
def normalize_title(title):
    return " ".join(title.lower().split())

# Remove duplicate stories
# Items are checked highest-weight source first
def dedupe(items):
    seen_links, seen_titles, unique = set(), set(), []
    for item in sorted(items, key=lambda i: i["weight"], reverse=True):
        link = normalize_link(item["link"]) if item["link"] else None
        title = normalize_title(item["title"])
        if (link and link in seen_links) or title in seen_titles:
            continue
        if link:
            seen_links.add(link)
        seen_titles.add(title)
        unique.append(item)
    return unique

# Remove items whose link was already posted
def drop_seen(items, seen_links):
    return [
        i for i in items
        if not i["link"] or normalize_link(i["link"]) not in seen_links
    ]