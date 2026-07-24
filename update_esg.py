#!/usr/bin/env python3
# Auto-updater: fetch latest SET ESG news (Google News RSS) and refresh esg_data.js.
# Runs on GitHub Actions daily. No AI/API key needed. Company data is preserved.
import json, re, urllib.request, xml.etree.ElementTree as ET, datetime, html

DATA_FILE = "esg_data.js"
THAI_MONTHS = ['','ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.']

def thai_date(dt):
    return f"{dt.day} {THAI_MONTHS[dt.month]} {dt.year+543}"

# 1) load current data
raw = open(DATA_FILE, encoding='utf-8').read()
payload = json.loads(raw[len('window.__ESG_SNAPSHOT='):].rstrip(';\n'))

# 2) fetch Google News RSS for SET ESG (Thai)
queries = [
    "SET ESG Thailand sustainability",
    "หุ้นไทย ESG ความยั่งยืน SET100",
]
new_items = []
seen = {n.get('url') for n in payload['n']} | {n.get('text') for n in payload['n']}
for q in queries:
    url = "https://news.google.com/rss/search?q=" + urllib.request.quote(q) + "&hl=th&gl=TH&ceid=TH:th"
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        xmldata = urllib.request.urlopen(req, timeout=30).read()
        root = ET.fromstring(xmldata)
        for item in root.iter('item'):
            title = html.unescape((item.findtext('title') or '').strip())
            link  = (item.findtext('link') or '').strip()
            pub   = (item.findtext('pubDate') or '').strip()
            src_el = item.find('{http://news.google.com/}source') or item.find('source')
            src = (src_el.text if src_el is not None else 'Google News')
            if not title or not link: continue
            if link in seen or title in seen: continue
            seen.add(link); seen.add(title)
            try:
                dt = datetime.datetime.strptime(pub[:16], '%a, %d %b %Y')
            except Exception:
                dt = datetime.datetime.utcnow()
            new_items.append({
                "ticker": [], "cat": ["G"], "dot": "#60A5FA", "sent": "neu",
                "text": title, "date": thai_date(dt), "src": src, "url": link
            })
    except Exception as e:
        print("fetch failed for", q, ":", e)

# 3) merge newest first, keep ~40 total
if new_items:
    payload['n'] = new_items[:10] + payload['n']
    payload['n'] = payload['n'][:40]

# 4) bump as-of date (always, even if no news)
today = datetime.datetime.utcnow() + datetime.timedelta(hours=7)  # Thailand time
payload['asOfDate'] = thai_date(today)
payload.setdefault('meta', {})['asOfDate'] = thai_date(today)
payload['meta']['retrievedAt'] = thai_date(today)
payload['savedAt'] = today.strftime('%d/%m/') + str(today.year+543) + " (auto GitHub)"

open(DATA_FILE, 'w', encoding='utf-8').write('window.__ESG_SNAPSHOT=' + json.dumps(payload, ensure_ascii=False) + ';')
print(f"added {len(new_items)} news | asOfDate {payload['asOfDate']} | total {len(payload['n'])}")
