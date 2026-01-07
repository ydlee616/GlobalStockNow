#!/usr/bin/env python3
# GlobalStockNow Collector v2.0 - 경제/기술 뉴스 대폭 강화 (2026.1.7)

import feedparser
import json
from datetime import datetime, timedelta

# 키워드 대폭 확장 (한국 관련 기업 + 글로벌 경제/기술)
KEYWORDS = [
    # 한국 기업
    'samsung', 'sk hynix', 'lg energy', 'hyundai', 'kia', 'posco', 'kakao', 'naver',
    # 글로벌 주요
    'nvidia', 'tesla', 'apple', 'microsoft', 'google', 'amazon', 'meta', 'intel', 'amd',
    'qualcomm', 'tsmc', 'asml',
    # 경제/기술 키워드
    'semiconductor', 'chip', 'hbm', 'ev', 'battery', 'ai', 'artificial intelligence',
    'quantum', '5g', '6g', 'oled', 'display', 'foundry', 'memory', 'dram', 'nand',
    'fed', 'interest rate', 'inflation', 'tariff', 'trade war', 'china', 'supply chain',
    'new product', 'launch', 'ces', 'earnings', 'revenue', 'profit', 'guidance'
]

def is_relevant(content):
    content_lower = content.lower()
    return any(kw.lower() in content_lower for kw in KEYWORDS)

def collect_news():
    print("속보 수집 시작 - 경제/기술 강화 버전")

    feeds = [
        # Business + Technology + World 우선
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5BU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",  # Business
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",  # Technology
        "https://news.google.com/rss/topics/CAAqKggKIiRDQkFTRlFvSUwyMHZNRGx1YlRZU0FtVnVLQUFQAQ?hl=en-US&gl=US&ceid=US:en",  # World
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp6ZEdBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",  # Science
        "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
    ]

    news_list = []
    cutoff = datetime.utcnow() - timedelta(hours=36)  # 범위 넓힘

    for url in feeds:
        feed = feedparser.parse(url)
        print(f"{url} → {len(feed.entries)}개 항목")

        for entry in feed.entries:
            if len(news_list) >= 40:
                break

            pub_parsed = entry.get('published_parsed')
            if not pub_parsed:
                continue
            pub_time = datetime(*pub_parsed[:6])
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
                    "summary": summary[:400]
                })

    unique = list({v['title']: v for v in news_list}.values())[:25]

    print(f"최종 {len(unique)}개 속보 수집")

    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    collect_news()
