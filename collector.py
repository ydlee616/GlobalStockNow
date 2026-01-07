#!/usr/bin/env python3
# GlobalStockNow Collector v3.3 - RSS 중심 + X 실시간 (오류 무시 안정 버전, 2026.1.8)
# RSS와 키워드 통일, CES 기간 자동 #CES2026 추가, X 실패 시 무시

import feedparser
import json
import subprocess
import datetime

# RSS와 X에 공통으로 사용하는 키워드 목록
COMMON_KEYWORDS = [
    # 한국 기업
    'samsung', 'lg', 'hyundai', 'kia', 'sk hynix', 'posco', 'kakao', 'naver', 'coupang',
    # 글로벌 주요 기업
    'nvidia', 'tesla', 'apple', 'microsoft', 'google', 'amazon', 'meta', 'intel', 'amd',
    'qualcomm', 'tsmc', 'asml', 'arm', 'broadcom',
    # 기술/경제 키워드
    'ces', 'ces 2026', 'micro rgb', 'oled', 'qd-oled', 'hbm', 'dram', 'nand', 'foundry',
    'ai', 'artificial intelligence', 'robot', 'humanoid', 'atlas', 'cloid', 'vision ai',
    'ev', 'battery', 'semiconductor', 'chip', 'supply chain', 'tariff', 'trade war',
    'earnings', 'guidance', 'revenue', 'profit', 'fed', 'interest rate'
]

# CES 기간 자동 감지 (2026년 1월 전체)
today = datetime.date.today()
is_ces_period = datetime.date(2026, 1, 1) <= today <= datetime.date(2026, 1, 31)

# X 쿼리 동적 생성
ces_hashtags = " OR #CES2026 OR #CES" if is_ces_period else ""
base_keywords = ' OR '.join([kw for kw in COMMON_KEYWORDS if not kw.startswith('#')])
X_QUERY = f"({base_keywords}){ces_hashtags} lang:en OR lang:ko"

def collect_from_rss():
    print("Google News RSS 수집 시작...")
    feeds = [
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5BU0FtVnVHZ0pWVXlnQVAB",  # Business
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdBU0FtVnVHZ0pWVXlnQVAB",  # Technology
        "https://news.google.com/rss/topics/CAAqKggKIiRDQkFTRlFvSUwyMHZNRGx1YlRZU0FtVnVLQUFQAQ",          # World
        "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
    ]
    
    news_list = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            print(f"  피드 처리: {len(feed.entries)}개 항목")
            for entry in feed.entries:
                title = entry.get('title', '')
                summary = entry.get('summary', '') or ''
                content = (title + " " + summary).lower()
                
                if any(kw.lower() in content for kw in COMMON_KEYWORDS):
                    news_list.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.get('published', datetime.datetime.utcnow().isoformat() + " UTC"),
                        "summary": summary[:600],
                        "source": "Google News"
                    })
        except Exception as e:
            print(f"  RSS 오류 (무시): {e}")
    
    print(f"  RSS 수집 완료: {len(news_list)}개")
    return news_list

def collect_from_x():
    print(f"X 실시간 수집 시도 중... (쿼리: {X_QUERY[:100]}...)")
    try:
        result = subprocess.check_output([
            "snscrape", "--jsonl", "--max-results", "50", "twitter-search", X_QUERY
        ], stderr=subprocess.DEVNULL, timeout=30).decode('utf-8', errors='ignore')
        
        posts = []
        for line in result.splitlines():
            if not line.strip():
                continue
            try:
                post = json.loads(line)
                posts.append({
                    "title": f"[X 속보] @{post['user']['username']}: {post['rawContent'][:160]}...",
                    "link": post['url'],
                    "published": post['date'],
                    "summary": post['rawContent'],
                    "source": "X (Twitter)"
                })
            except:
                continue
        
        print(f"  X 수집 성공: {len(posts)}개")
        return posts
    except Exception as e:
        print(f"  X 수집 실패 (정상 - 무시하고 RSS로 진행): {str(e)[:100]}")
        return []  # 실패해도 빈 리스트 → 파이프라인 계속

def collect_news():
    print("\n=== 글로벌스톡나우 속보 수집 시작 (v3.3) ===\n")
    
    rss_news = collect_from_rss()
    x_news = collect_from_x()
    
    # 모든 뉴스 합치기 + 중복 제거 (link 기준)
    all_news = rss_news + x_news
    seen = set()
    unique_news = []
    for item in all_news:
        if item['link'] not in seen:
            seen.add(item['link'])
            unique_news.append(item)
    
    # 최신순 정렬
    unique_news.sort(key=lambda x: x['published'], reverse=True)
    
    # 최대 40개
    final_news = unique_news[:40]
    
    # 파일 저장
    with open('breaking_news.json', 'w', encoding='utf-8') as f:
        json.dump(final_news, f, indent=2, ensure_ascii=False)
    
    print(f"\n최종 수집 완료: 총 {len(final_news)}개")
    print(f"  ├─ Google News RSS: {len(rss_news)}개")
    print(f"  └─ X 실시간: {len(x_news)}개")
    print("\n=== 수집 종료 ===\n")

if __name__ == "__main__":
    collect_news()
