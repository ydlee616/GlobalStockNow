#!/usr/bin/env python3
# GlobalStockNow News Collector v0.3 (2026.1.3)
# 정확한 주식/경제 속보 필터링 강화 버전

import feedparser
import json
import re
from datetime import datetime, timedelta

# 엄격한 주식·경제 키워드 (대소문자 무시, 단어 경계 매칭)
KEY_PHRASES = [
    'nvidia', 'amd', 'intel', 'tsmc', 'samsung electronics', 'sk hynix', 'semiconductor', 'chip shortage',
    'federal reserve', 'fed', 'powell', 'interest rate', 'rate cut', 'rate hike', 'fomc',
    'tesla', 'cybertruck', 'model y', 'model 3', 'ev sales',
    'apple', 'iphone', 'aapl earnings',
    'microsoft', 'msft', 'amazon', 'amzn', 'meta', 'google stock', 'alphabet',
    'oil price', 'brent crude', 'wti', 'opec',
    'trade war', 'tariff', 'china economy',
    'bitcoin', 'btc', 'ethereum', 'crypto regulation'
]

def is_relevant_news(title, summary=""):
    content = (title + " " + summary).lower()
    for phrase in KEY_PHRASES:
        # 단어 경계(\b)로 정확히 매칭
        if re.search(r'\b' + re.escape(phrase) + r'\b', content):
            return True
    return False

def collect_news():
    print("GlobalStockNow 속보 수집 시작")

    feeds = [
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5BU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",  # Business
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",  # Technology
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en"   # World (보조)
    ]

    news_list = []
    cutoff = datetime.utcnow() - timedelta(hours=8)  # 최근 8시간

    for url in feeds:
        feed = feedparser.parse(url)
        print(f"{url} → {len(feed.entries)}개 항목 확인")

        for entry in feed.entries:
            pub_parsed = entry.get('published_parsed')
            if not pub_parsed:
                continue
            pub_time = datetime(*pub_parsed[:6])

            if pub_time < cutoff:
                continue

            title = entry.title
            summary = entry.get('summary', '') or ''

            if is_relevant_news(title, summary):
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

    print(f"최종 {len(unique)}개 주식 관련 속보 수집 완료")

    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print("breaking_news.json 저장 완료")

if __name__ == "__main__":
    collect_news()
