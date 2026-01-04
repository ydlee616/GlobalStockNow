#!/usr/bin/env python3
# GlobalStockNow News Collector v0.7 - 필터 강화 버전 (2026.1.3)

import feedparser
import json
from datetime import datetime, timedelta
import re

# 정제된 키워드 (주식/경제 특정 용어 위주)
KEYWORDS = [
    'nvidia', 'amd', 'intel', 'tsmc', 'samsung electronics', 'sk hynix', 'semiconductor', 'chip shortage',
    'fed', 'federal reserve', 'interest rate', 'powell', 'fomc', 'rate cut',
    'tesla', 'ev sales', 'cybertruck',
    'apple', 'iphone', 'aapl', 'microsoft', 'msft', 'amazon', 'amzn', 'meta',
    'oil price', 'opec', 'brent', 'wti',
    'bitcoin price', 'btc', 'crypto market', 'ethereum',
    'trade war', 'tariff', 'china economy'
]

def is_relevant(content):
    content_lower = content.lower()
    for kw in KEYWORDS:
        if re.search(r'\b' + re.escape(kw.lower()) + r'\b', content_lower):
            return True
    return False

def collect_news():
    print("속보 수집 시작 - 강화 버전")

    feeds = [
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5BU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",  # Business
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en"   # Technology
    ]

    news_list = []
    cutoff = datetime.utcnow() - timedelta(hours=12)

    for url in feeds:
        feed = feedparser.parse(url)
        print(f"{url} → {len(feed.entries)}개 항목")

        for entry in feed.entries:
            pub_parsed = entry.get('published_parsed')
            if pub_parsed:
                pub_time = datetime(*pub_parsed[:6])
            else:
                continue

            if pub_time < cutoff:
                continue

            title = entry.title
            summary = entry.get('summary', '') or ''
            content = title + " " + summary

            if is_relevant(content):
                news_list.append({
                    "title": title,
                    "link": entry.link,
                    "published": pub_time.strftime("%Y-%m-%d %H:%M UTC"),
                    "summary": summary[:300]
                })

            if len(news_list) >= 20:
                break

    # 중복 제거
    seen = set()
    unique = []
    for item in news_list:
        if item['title'] not in seen:
            seen.add(item['title'])
            unique.append(item)

    print(f"최종 {len(unique)}개 속보 수집")

    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print("breaking_news.json 저장 완료")

if __name__ == "__main__":
    collect_news()
