#!/usr/bin/env python3
# GlobalStockNow News Collector v0.1 (2026.1.3)
# Google News RSS로 해외 주식 속보 수집

import feedparser
from datetime import datetime, timedelta
import json

# 키워드 리스트 (30개 이상)
STOCK_KEYWORDS = [
    'nvidia', 'amd', 'intel', 'tsmc', 'samsung', 'sk hynix', 'semiconductor', 'chip',
    'fed', 'federal reserve', 'interest rate', 'powell',
    'tesla', 'ev', 'battery', 'byd',
    'apple', 'iphone', 'aapl', 'google', 'msft', 'amazon', 'meta',
    'oil', 'opec', 'energy',
    'china', 'trade war', 'tariff',
    'bitcoin', 'crypto', 'ethereum'
]

def collect_breaking_news(max_hours=6, max_items=20):
    print(f"🚀 GlobalStockNow 속보 수집 시작 (최근 {max_hours}시간, 최대 {max_items}개)")

    rss_feeds = [
        'https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en',
        'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en',  # World
        'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5BU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en',  # Business
        'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en'   # Technology
    ]

    all_news = []
    cutoff_time = datetime.utcnow() - timedelta(hours=max_hours)

    for feed_url in rss_feeds:
        feed = feedparser.parse(feed_url)
        print(f"📡 {feed_url}에서 {len(feed.entries)}개 기사 수집")

        for entry in feed.entries:
            if len(all_news) >= max_items * 2:  # 여유 있게
                break

            pub_time = entry.get('published_parsed')
            if not pub_time:
                continue
            pub_dt = datetime(*pub_time[:6])
            if pub_dt < cutoff_time:
                continue

            title = entry.title.lower()
            summary = (entry.get('summary', '') or '').lower()
            content = title + ' ' + summary

            matched = [kw for kw in STOCK_KEYWORDS if kw.lower() in content]
            if matched:
                all_news.append({
                    'title': entry.title,
                    'link': entry.link,
                    'published': pub_dt.strftime('%Y-%m-%d %H:%M UTC'),
                    'keywords': matched[:3],
                    'summary': entry.get('summary', '')[:200]
                })

    # 중복 제거 및 정렬
    seen = set()
    unique_news = []
    for item in all_news:
        if item['title'] not in seen:
            seen.add(item['title'])
            unique_news.append(item)

    final_news = unique_news[:max_items]

    print(f"✅ 최종 {len(final_news)}개 속보 선별 완료!")

    # TOP 5 출력
    print("\n📊 수집된 주요 속보:")
    for i, item in enumerate(final_news[:5], 1):
        print(f"{i}. {item['title']}")
        print(f"   링크: {item['link']}")
        print(f"   키워드: {', '.join(item['keywords'])}")
        print()

    # JSON 저장
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(final_news, f, indent=2, ensure_ascii=False)

    print("💾 breaking_news.json 저장 완료")

if __name__ == "__main__":
    collect_breaking_news()
