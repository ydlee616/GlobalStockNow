#!/usr/bin/env python3
# GlobalStockNow News Collector v0.5 - 필터 완화 + 안정화 (2026.1.3)

import feedparser
import json
from datetime import datetime, timedelta
import re

# 완화된 키워드 (주식/경제 관련 주요 단어)
KEYWORDS = [
    'nvidia', 'amd', 'intel', 'tsmc', 'samsung', 'sk hynix', 'semiconductor', 'chip',
    'fed', 'federal reserve', 'interest rate', 'powell', 'fomc',
    'tesla', 'ev', 'battery', 'cybertruck',
    'apple', 'iphone', 'microsoft', 'amazon', 'meta', 'google',
    'oil', 'opec', 'brent', 'wti',
    'bitcoin', 'btc', 'crypto', 'ethereum',
    'trade war', 'tariff', 'china', 'hong kong stock'
]

def is_relevant(title, summary=""):
    content = (title + " " + summary).lower()
    for kw in KEYWORDS:
        if kw.lower() in content:
            return True
    return False

def collect_news(max_items=15, hours=8):
    print("GlobalStockNow 속보 수집 시작 (필터 완화 버전)")

    feeds = [
        "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",  # Google News Top
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5BU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",  # Business
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",  # Technology
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en"   # World
    ]

    news_list = []
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    for url in feeds:
        try:
            feed = feedparser.parse(url)
            print(f"{url} → {len(feed.entries)}개 항목 확인")
        except Exception as e:
            print(f"피드 로딩 실패: {e}")
            continue

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

            if is_relevant(title, summary):
                news_list.append({
                    "title": title,
                    "link": entry.link,
                    "published": pub_time.strftime("%Y-%m-%d %H:%M UTC"),
                    "summary": summary[:300]
                })

            if len(news_list) >= max_items * 2:
                break

    # 중복 제거
    seen = set()
    unique = []
    for item in news_list:
        if item['title'] not in seen:
            seen.add(item['title'])
            unique.append(item)

    final = unique[:max_items]

    print(f"최종 {len(final)}개 속보 수집 완료")

    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print("breaking_news.json 저장 완료")

if __name__ == "__main__":
    collect_news()
