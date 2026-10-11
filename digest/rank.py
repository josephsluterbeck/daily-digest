import re

# Sum the weights of keywords that appear in text as whole words
def _keyword_hits(text, keywords):
    return sum(
        (weight or 1)
        for kw, weight in keywords.items()
        if re.search(rf"\b{re.escape}\b", text, re.IGNORECASE)
    )

# Score = (keyword hits in title x 2 + hits in summary) x source weight
def score(item, keywords):
    title_hits = _keyword_hits(item["title"], keywords)
    summary_hits = _keyword_hits(item["summary"], keywords)
    return (title_hits * 2 + summary_hits) * item["weight"]

# Pick the best item from each category in config order
def pick_top(items, categories, keywords, max_items):
    picks = []
    for category in categories:
        pool = [i for i in items if i["category"] == category]
        if not pool:
            print(f"No recent items for {category}")
            continue
        best = max(pool, key=lambda i: (score(i, keywords), i["weight"], i["published"]))
        picks.append(best)
    return picks[:max_items]