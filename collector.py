#!/usr/bin/env python3
# GlobalStockNow Collector v1.1 - 영문 키워드 + 신기술/신상품 강화 (2026.1.6)

import feedparser
import json
from datetime import datetime, timedelta

# 모든 키워드 영문화 (신기술/신상품 중심)
KEYWORDS = [
    'nvidia', 'tesla', 'fed', 'oil', 'bitcoin', 'semiconductor', 'ev', 'apple', 'microsoft', 'amazon',
    'samsung', 'sk hynix', 'interest rate', 'crypto', 'tariff', 'china',
    'new product', 'launch', 'ces', 'ai', 'quantum', 'new chip', 'new phone', 'new car', 'new battery',
    'new technology', 'breakthrough', 'innovation', 'unveiled', 'announced', 'released'
]

def is_relevant(content):
    content_lower = content.lower()
    return any(kw.lower() in content_lower for kw in KEYWORDS)

def collect_news():
    print("속보 수집 시작 - 영문 키워드 + 신기술 강화 버전")

    feeds = [
        # Business
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5BU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
        # Technology (신기술/신상품 핵심)
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
        # Science (신기술 추가)
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp6ZEdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
        # Top News
        "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
    ]

    news_list = []
    cutoff = datetime.utcnow() - timedelta(hours=24)

    for url in feeds:
        feed = feedparser.parse(url)
        print(f"{url} → {len(feed.entries)}개 항목 확인")

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
    unique = list({item['title']: item for item in news_list}.values())[:20]

    print(f"최종 {len(unique)}개 속보 수집 완료")

    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print("breaking_news.json 저장 완료")

if __name__ == "__main__":
    collect_news()
