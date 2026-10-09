import os, requests
from dotenv import load_dotenv

load_dotenv()

def send(content="", embeds=None):
    url = os.environ["DISCORD_WEBHOOK_URL"]
    r = requests.post(url, json={"content": content, "embeds": embeds or []}, timeout=15)
    r.raise_for_status()

send("Hello from daily digest", [{
    "title": "Test Item",
    "url": "https://example.com",
    "description": "If you see this, it means the daily digest is working.",
    "color": 0x5865F2
}])