#!/usr/bin/env python3
"""Deals watcher: fetch r/deals, filter with a free LLM, Telegram the good ones.

Her bar (2026-10-16): only alert on something GOOD - an opportunity she can act
on, with a deadline. Most days: silence.
"""
import json, os, re, sys, time, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "5178282156")
INTERESTS = (
    "art supplies (paints, paper, brushes, canvas), home/kitchen items, "
    "electronics, everyday shopping for one person in Los Angeles"
)

def fetch(max_items=25):
    req = urllib.request.Request("https://www.reddit.com/r/deals/.rss?limit=25",
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", errors="replace")
    entries = re.findall(r"<entry>(.*?)</entry>", page, re.S)
    out = []
    for e in entries[:max_items]:
        t = re.search(r"<title[^>]*>(.*?)</title>", e, re.S)
        if t:
            out.append(t.group(1))
    return out

def llm_filter(titles):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    corpus = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
    prompt = (
        "You filter deals for one person. Her interests: " + INTERESTS + ".\n"
        "Her bar: only deals that are a GENUINELY GOOD opportunity she could act "
        "on soon - a real discount on something useful, not niche gamer gear, not "
        "news, not a price rise.\n"
        "Deals:\n" + corpus + "\n\n"
        "Return JSON: {\"picks\": [{\"n\": <number>, \"why\": \"<10 words max>\"}]}"
        " with at most 3 picks, or an empty list if nothing clears the bar. "
        "JSON only, no other text."
    )
    payload = {"model": "openai/gpt-oss-120b", "messages": [{"role": "user", "content": prompt}],
               "max_tokens": 500, "temperature": 0.2}
    for attempt in range(3):
        try:
            req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(payload).encode(),
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                         "User-Agent": "curl/8.5.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                resp = json.load(r)
            txt = resp["choices"][0]["message"].get("content", "").strip()
            m = re.search(r"\{.*\}", txt, re.S)
            return json.loads(m.group(0)) if m else {"picks": []}
        except Exception as ex:
            if attempt == 2:
                print(f"filter error: {ex}", file=sys.stderr)
                return None
            time.sleep(2 ** attempt)

def telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("DRY RUN (no token) - would send:\n" + text)
        return
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode())
    with urllib.request.urlopen(req, timeout=30) as r:
        json.load(r)
    print("sent")

def main():
    dry = "--dry" in sys.argv
    titles = fetch()
    if not titles:
        print("no deals fetched"); return
    picks = llm_filter(titles)
    if picks is None:
        # Infrastructure failure must be LOUD: exit non-zero so the Actions run
        # shows red. Silence (exit 0) is reserved for "nothing clears the bar".
        print("filter failed - secrets missing or LLM unreachable"); sys.exit(1)
    if not picks.get("picks"):
        print("nothing clears the bar today - silence"); return
    lines = ["Good deals today:"]
    for p in picks["picks"][:3]:
        n = p.get("n", 0)
        if 1 <= n <= len(titles):
            lines.append(f"- {titles[n-1]} ({p.get('why','')})")
    if len(lines) == 1:
        print("nothing usable after mapping"); return
    if dry:
        print("WOULD SEND:\n" + "\n".join(lines))
    else:
        telegram("\n".join(lines))

if __name__ == "__main__":
    main()
