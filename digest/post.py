import os, requests
from dotenv import load_dotenv

MAX_EMBEDS = 10
MAX_TOTAL_CHARS = 6000

load_dotenv()

# Send a message to the Discord webhook
# Raises an exception if the request fails
def send(content="", embeds=None):
    url = os.environ["DISCORD_WEBHOOK_URL"]
    r = requests.post(url, json={"content": content, "embeds": embeds or []}, timeout=15)
    r.raise_for_status()

# Count the characters Discord includes in the 6,000 character limit
def embed_length(embed):
    return (
        len(embed.get("title", ""))
        + len(embed.get("description", ""))
        + len(embed.get("author", {}).get("name", ""))
        + len(embed.get("footer", {}).get("text", ""))
        + sum(len(f.get("name", "")) + len(f.get("value", ""))
              for f in embed.get("fields", []))
    )

# Trim the list to Discord's limits
def fit_to_limits(embeds):
    embeds = embeds[:MAX_EMBEDS]
    while embeds and sum(embed_length(e) for e in embeds) > MAX_TOTAL_CHARS:
        embeds = embeds[:-1]
    return embeds

if __name__ == "__main__":
    send("Hello from daily digest", [{
    "title": "Test Item",
    "url": "https://example.com",
    "description": "If you see this, it means the daily digest is working.",
    "color": 0x5865F2
    }])