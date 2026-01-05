#!/usr/bin/env python3
# GlobalStockNow News Collector v0.8 - 균형 필터 버전 (2026.1.6)

import feedparser
import json
from datetime import datetime, timedelta
import re

# 균형 잡힌 키워드 (정확 매칭 + 일부 일반 단어 허용)
KEYWORDS = [
    'nvidia', 'amd', 'intel', 'tsmc', 'samsung', 'sk hynix', 'semiconductor', 'chip',
    'fed', 'federal reserve', 'interest rate', 'powell', 'fomc',
    'tesla', 'ev', 'cybertruck', 'model',
    'apple', 'iphone', 'microsoft', 'amazon', 'meta', 'google',
    'oil', 'opec', 'brent', 'wti',
    'bitcoin', 'btc', 'crypto', 'ethereum',
    'trade war', 'tariff', 'china'
]

def is_relevant(content):
    content_lower = content.lower()
    for kw in KEYWORDS:
        if kw.lower() in content_lower:  # 간단한 포함 매칭 (오매칭 최소화)
            return True
    return False

def collect_news():
    print("속보 수집 시작 - 균형 버전")

    feeds = [
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5BU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",  # Business
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",  # Technology
        "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"  # Top News 추가 (보완)
    ]

    news_list = []
    cutoff = datetime.utcnow() - timedelta(hours=24)  # 최근 24시간 확대

    for url in feeds:
        feed = feedparser.parse(url)
        print(f"{url} → {len(feed.entries)}개 항목")

        for entry in feed.entries:
            if len(news_list) >= 30:
                break

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

    # 중복 제거
    seen = set()
    unique = []
    for item in news_list:
        if item['title'] not in seen:
            seen.add(item['title'])
            unique.append(item)

    final = unique[:20]

    print(f"최종 {len(final)}개 속보 수집")

    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    collect_news()
