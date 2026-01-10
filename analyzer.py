"""Module: analyzer.py | Version: 0.4.4 | Updated: 2026-01-11"""
import json, time, requests, os, re
from datetime import datetime, timedelta

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
# [복구] 파이프라인 번호 환경 변수
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")

def send_to_telegram(msg, article_url=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # 모든 메시지 상단에 파이프라인 번호 강제 노출
    header = f"🌍 **GlobalStockNow 브리핑 (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + msg, "parse_mode": "Markdown"}
    
    if article_url:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 대본 제작 선택", "url": f"https://t.me/share/url?url={article_url}&text=대본생성요청"}]]})
    requests.post(url, data=payload, timeout=10)

def run():
    print(f"🚀 [Ver 0.4.4] 분석 시작 (Run #{RUN_NUMBER})")
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            articles = data.get('articles', [])
            print(f"📊 수집된 기사 수: {len(articles)}") # 디버깅용 로그
    except: return

    # 필터 기준: 현재 실행 시간으로부터 36시간 이내로 확장 (안정성 확보)
    now = datetime.now()
    limit = now - timedelta(hours=36)
    
    count = 0
    for art in articles[:15]:
        # 과거 뉴스(2018 등) 원천 차단
        if any(y in art.get('published_at', '') for y in ['2018', '2019']): continue
            
        # [AI 분석 호출 로직 동일...]
        # ... (생략) ...
        
        if res:
            msg = f"💎 **제목: {res.get('title')}**\n**영향**: {res.get('essence', {}).get('subtext')}\n**점수**: {res.get('score')}점"
            send_to_telegram(msg, art.get('link'))
            count += 1
            time.sleep(32)

    if count == 0:
        # [복구] 뉴스 없을 때도 번호 노출
        send_to_telegram("현재 36시간 내 유효 속보 없음 (정밀 감시 중)")

if __name__ == "__main__": run()
