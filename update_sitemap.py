import requests
from bs4 import BeautifulSoup
import hashlib
import json
import datetime
import os
import xml.etree.ElementTree as ET

# -----------------------------
# CONFIGURATION
# -----------------------------
MONITORED_URLS = [
    "https://gasheads.org/board/2/gas-guzzler",
    "https://gasheads.org/board/3/general-football-chat",
    "https://gasheads.org/",
    "https://gasheads.org/board/20/match-day-threads",
    "https://gasheads.org/page/sitemap2",
    "https://gasheads.org/page/volunteer",
    "https://gasheads.org/page/contact-us"
]

STATE_FILE = ".state.json"
SITEMAP_FILE = "sitemap.xml"

TODAY = datetime.date.today().isoformat()

# Browser headers to bypass ProBoards bot protection
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# -----------------------------
# HELPERS
# -----------------------------
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def fetch_html(url):
    """Fetch HTML with browser headers to avoid 409 errors."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"ERROR fetching {url}: {e}")
        return None


def extract_board_timestamp(html):
    """Extract newest <time datetime=""> tag from a ProBoards board page."""
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    time_tags = soup.select("time")

    if not time_tags:
        return None

    timestamps = [t.get("datetime") for t in time_tags if t.get("datetime")]
    return max(timestamps) if timestamps else None


def hash_page(html):
    return hashlib.sha256(html.encode("utf-8")).hexdigest() if html else None


def update_sitemap(urls_to_update):
    tree = ET.parse(SITEMAP_FILE)
    root = tree.getroot()

    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    for url in urls_to_update:
        for url_node in root.findall("ns:url", ns):
            loc = url_node.find("ns:loc", ns)
            lastmod = url_node.find("ns:lastmod", ns)

            if loc is not None and loc.text == url:
                if lastmod is None:
                    lastmod = ET.SubElement(url_node, "lastmod")
                lastmod.text = TODAY

    tree.write(SITEMAP_FILE, encoding="utf-8", xml_declaration=True)


# -----------------------------
# MAIN LOGIC
# -----------------------------
def main():
    print("Loading previous state...")
    state = load_state()
    new_state = {}
    changed_urls = []

    for url in MONITORED_URLS:
        print(f"Checking {url}...")
        html = fetch_html(url)

        if html is None:
            print(f"Skipping {url} due to fetch error.")
            new_state[url] = state.get(url)  # preserve old value
            continue

        if "/board/" in url:
            ts = extract_board_timestamp(html)
