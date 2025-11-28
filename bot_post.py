#!/usr/bin/env python3
"""
Automated Telegram Poster for Mixed Content (GitHub Actions)

Dependencies: requests, feedparser
Behavior:
 - Fetches items from RSS & APIs
 - Avoids reposts by tracking IDs in posted_ids.json
 - Sends nicely formatted messages to a Telegram channel
 - Updates posted_ids.json and commits changes back to the repo (uses GITHUB_TOKEN in Actions)
"""

import os
import sys
import json
import time
import random
import hashlib
from datetime import datetime
from pathlib import Path

import requests
import feedparser

# -----------------------
# CONFIG - change nothing here unless you know what you're doing
# -----------------------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")   # set in GitHub Secrets
CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")  # set in GitHub Secrets (use @channelusername or -1001234567890)
REPO_WORKDIR = Path(".")  # GitHub Actions runner workspace (repo root)
POSTED_DB = REPO_WORKDIR / "posted_ids.json"
MAX_MESSAGES_PER_RUN = 6   # number of new items to post each run (tweak if you want fewer)
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
# -----------------------

# Content sources (RSS + APIs)
RSS_FEEDS = {
    "Tech": "https://techcrunch.com/feed/",
    "Crypto": "https://cointelegraph.com/rss",
    "Finance": "https://www.investing.com/rss/news.rss",
    "AI News": "https://venturebeat.com/category/ai/feed/",
    "General Knowledge": "https://www.sciencenews.org/feed"
}


ZEN_QUOTES_API = "https://zenquotes.io/api/random"
RANDOM_FACT_API = "https://uselessfacts.jsph.pl/random.json?language=en"

# small bank of quick finance tips — these are local and free
FINANCE_TIPS = [
    "Start with a written budget and track it weekly.",
    "Always have an emergency fund equal to 3–6 months of expenses.",
    "Dollar-cost averaging reduces timing risk for investments.",
    "Avoid checking investments daily — it causes emotional trading.",
    "Diversify: different assets perform differently in market cycles."
]

# utility functions
def load_posted_db():
    if not POSTED_DB.exists():
        return {"ids": []}
    try:
        return json.loads(POSTED_DB.read_text(encoding="utf8"))
    except Exception:
        return {"ids": []}

def save_posted_db(db):
    POSTED_DB.write_text(json.dumps(db, indent=2), encoding="utf8")

def sha_id(s):
    return hashlib.sha1(s.encode("utf8")).hexdigest()

def send_telegram_message(text, parse_mode="HTML"):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set.")
        return False
    url = TELEGRAM_API + "/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }
    r = requests.post(url, json=payload, timeout=20)
    if r.status_code == 200:
        return True
    else:
        print("Telegram send failed:", r.status_code, r.text)
        return False

def fetch_rss_items():
    items = []
    for name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:6]:
                title = e.get("title", "").strip()
                link = e.get("link", "").strip()
                published = e.get("published", "") or e.get("pubDate", "")
                summary = (e.get("summary", "") or "") 
                uid = sha_id(name + title + link)
                items.append({
                    "id": uid,
                    "source": name,
                    "title": title,
                    "link": link,
                    "published": published,
                    "summary": summary
                })
        except Exception as ex:
            print(f"Failed RSS {name}: {ex}")
    return items

def fetch_quote():
    try:
        r = requests.get(ZEN_QUOTES_API, timeout=10)
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            q = data[0]
            return f"💬 <b>{q.get('q')}</b>\n— <i>{q.get('a')}</i>"
    except Exception:
        pass
    return None

def fetch_random_fact():
    try:
        r = requests.get(RANDOM_FACT_API, timeout=10)
        j = r.json()
        return f"🧠 <b>Random Fact:</b> {j.get('text')}"
    except Exception:
        pass
    return None

def pick_finance_tip():
    return "💹 <b>Finance Tip:</b> " + random.choice(FINANCE_TIPS)

# Compose message nicely
def format_article_msg(item):
    title = item.get("title") or "Untitled"
    link = item.get("link") or ""
    source = item.get("source") or ""
    published = item.get("published") or ""
    summary = item.get("summary") or ""
    lines = []
    lines.append("📰 <b>" + title + "</b>")
    if source:
        lines.append(f"🔹 <i>{source}</i> {published}")
    if summary:
        # keep summary short
        s = summary
        if len(s) > 350:
            s = s[:347] + "..."
        lines.append(s)
    if link:
        lines.append(f"🔗 <a href=\"{link}\">Read more</a>")
    return "\n".join(lines)

# Git commit helper (used in Actions environment)
def commit_and_push_changes(commit_message="Update posted_ids.json"):
    """
    This function assumes:
     - Git is available
     - GITHUB_TOKEN exists in env and actions checked out the repo
    The workflow will provide GITHUB_TOKEN and configure git.
    """
    try:
        # Only commit if file changed
        os.system("git add posted_ids.json || true")
        # check diff
        res = os.popen("git status --porcelain").read().strip()
        if not res:
            print("No changes to commit.")
            return True
        os.system('git config user.email "actions@github.com"')
        os.system('git config user.name "GitHub Actions"')
        os.system(f'git commit -m "{commit_message}" || true')
        # push using environment-provided token (workflow sets it up)
        # remote already exists; push
        push_result = os.system('git push origin HEAD:$GITHUB_REF || git push')
        if push_result == 0:
            print("Committed and pushed posted_ids.json")
            return True
        else:
            print("Push may have failed (non-zero exit).")
            return False
    except Exception as ex:
        print("Commit failed:", ex)
        return False

def main():
    db = load_posted_db()
    posted = set(db.get("ids", []))
    new_posted = []

    # Aggregate candidate items
    candidates = []

    # 1) RSS items
    rss_items = fetch_rss_items()
    candidates.extend(rss_items)

    # 2) Quote
    q = fetch_quote()
    if q:
        uid = sha_id("quote-" + q)
        candidates.append({
            "id": uid,
            "source": "Quote",
            "title": q,
            "link": "",
            "published": "",
            "summary": ""
        })

    # 3) Random fact
    rf = fetch_random_fact()
    if rf:
        uid = sha_id("fact-" + rf)
        candidates.append({
            "id": uid,
            "source": "Fact",
            "title": rf,
            "link": "",
            "published": "",
            "summary": ""
        })

    # 4) Finance tip
    tip = pick_finance_tip()
    uid = sha_id("tip-" + tip)
    candidates.append({
        "id": uid,
        "source": "FinanceTip",
        "title": tip,
        "link": "",
        "published": "",
        "summary": ""
    })

    # Shuffle to get mixed content order
    random.shuffle(candidates)

    posted_count = 0
    for item in candidates:
        if posted_count >= MAX_MESSAGES_PER_RUN:
            break
        item_id = item["id"]
        if item_id in posted:
            continue
        # Format and send
        if item.get("source") in ["Quote", "Fact", "FinanceTip"]:
            text = item["title"]
        else:
            text = format_article_msg(item)

        # add a little time stamp footer
        footer = f"\n\n⏱️ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        text = text + footer

        ok = send_telegram_message(text)
        if ok:
            print("Posted:", item.get("title")[:80])
            posted.add(item_id)
            new_posted.append(item_id)
            posted_count += 1
            # small delay to be polite to API
            time.sleep(2)
        else:
            print("Failed to post item:", item.get("title")[:80])

    # save db
    db["ids"] = list(posted)[-5000:]  # keep last 5000 ids to bound file size
    save_posted_db(db)

    # If running in Actions, commit posted_ids.json back
    if os.environ.get("GITHUB_ACTIONS", "") == "true":
        commit_and_push_changes("chore: update posted_ids.json (automation)")

    print("Run complete. Posted:", posted_count, "items.")

if __name__ == "__main__":
    main()

