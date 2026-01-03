#!/usr/bin/env python3
# GlobalStockNow News Collector v0.6 - 완전 안정화 버전 (2026.1.3)

import feedparser
import json
from datetime import datetime, timedelta

# 주식 관련 키워드 (완화된 버전)
KEYWORDS = [
    'nvidia', 'amd', 'intel', 'tsmc', 'samsung', 'sk hynix', 'semiconductor', 'chip',
    'fed', 'federal reserve', 'interest rate', 'powell', 'fomc',
    'tesla', 'ev', 'cybertruck', 'model',
    'apple', 'iphone', 'microsoft', 'amazon', 'meta', 'google', 'alphabet',
    'oil', 'opec', 'brent', 'wti',
    'bitcoin', 'btc', 'crypto', 'ethereum',
    'trade', 'tariff', 'china', 'hong kong'
]

def is_relevant(title, summary=""):
    content = (title + " " + summary).lower()
    for kw in KEYWORDS:
        if kw.lower() in content:
            return True
    return False

def collect_news():
    print("GlobalStockNow 속보 수집 시작 - 필터 완화 버전")

    feeds = [
        "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",  # Top News
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5BU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",  # Business
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",  # Technology
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en"   # World
    ]

    news_list = []
    cutoff = datetime.utcnow() - timedelta(hours=12)  # 최근 12시간

    for url in feeds:
        feed = feedparser.parse(url)
        if feed.bozo:
            print(f"피드 파싱 오류: {url}")
            continue

        print(f"{url} → {len(feed.entries)}개 항목 확인")

        for entry in feed.entries:
            if len(news_list) >= 30:
                break

            pub_time = entry.get('published_parsed')
            if not pub_time:
                continue
            pub_dt = datetime(*pub_time[:6])
            if pub_dt < cutoff:
                continue

            title = entry.title
            summary = entry.get('summary', '') or ''

            if is_relevant(title, summary):
                news_list.append({
                    "title": title,
                    "link": entry.link,
                    "published": pub_dt.strftime("%Y-%m-%d %H:%M UTC"),
                    "summary": summary[:300]
                })

    # 중복 제거
    seen_titles = set()
    unique_news = []
    for item in news_list:
        if item['title'] not in seen_titles:
            seen_titles.add(item['title'])
            unique_news.append(item)

    final_news = unique_news[:15]  # 최대 15개

    print(f"최종 {len(final_news)}개 속보 수집 완료")

    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(final_news, f, indent=2, ensure_ascii=False)

    print("breaking_news.json 저장 완료")

if __name__ == "__main__":
    collect_news()
