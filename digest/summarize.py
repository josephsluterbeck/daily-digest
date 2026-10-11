import os
import requests
import trafilatura
from fetch import USER_AGENT

MODELS_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

# Cap on article text sent to the model
MAX_INPUT_CHARS = 4000

PROMPT = (
    "Summarize this news article in 2-3 short, plain sentences. "
    "State the key facts only: who, what, and why it matters. "
    "Do not start with phrases like 'This article' or 'The author'. "
    "Keep it under 350 characters."
)

# Download an article page and extract its main text with trafilatura
# Return none if the page can't be downloaded or has no readable text
def fetch_article_text(url):
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f" Couldn't download article: {e}")
        return None
    text = trafilatura.extract(r.text)
    return " ".join(text.split()) if text else None

# Shorten text to at most 'limit' characters
# Fall back to hard cut if first sentence is too long
def trim_to_sentence(text, limit=400):
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if end > limit * 0.4:
        return cut[: end + 1]
    return cut.rstrip() + "..."

# Ask GitHub Models for a short summary of the article
# Raise an exception on any failure (rate limit, bad model ID, or outage)
def ai_summary(title, text, model, token):
    r = requests.post(
        MODELS_ENDPOINT,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": f"Title: {title}\n\n{text[:MAX_INPUT_CHARS]}"},
            ],
            "temperature": 0.3,
            "max_tokens": 1024,
            "reasoning_effort": "minimal",
        },
        timeout=30
    )
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    try:
        data = r.json()
    except ValueError:
        raise RuntimeError(
            f"Non-JSON response (status {r.status_code}, "
            f"{r.headers.get('Content-Type')}): {r.text[:200]!r}"
        )
    return r.json()["choices"][0]["message"]["content"].strip()

# Replace item["summary"] with best summary available
# Otherwise keep the RSS summary
def summarize_item(item, model, max_chars = 400):
    print(f"Summarizing [{item['source']}] {item['title'][:60]}")
    text = fetch_article_text(item["link"])
    if not text:
        print(" -> using RSS summary")
        return

    token = os.environ.get("GEMINI_API_KEY")
    if token:
        try:
            item["summary"] = trim_to_sentence(ai_summary(item["title"], text, model, token), max_chars)
            print(" -> AI summary")
            return
        except Exception as e:
            print(f" AI summary failed: {e}")
    item["summary"] = trim_to_sentence(text, max_chars)
    print(" -> article lead")