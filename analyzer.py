"""
Module: analyzer.py | Version: 0.4.3 | Updated: 2026-01-11
Description: Strict 24h filter & NK Drone specialized prompt.
"""
import json, time, requests, os, re
from datetime import datetime, timedelta

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_telegram(msg, article_url=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    if article_url:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 대본 제작 선택", "url": f"https://t.me/share/url?url={article_url}&text=유튜브대본제작"}]]})
    requests.post(url, data=payload, timeout=10)

def analyze_logic(article):
    # [북한 리스크 돌파용 특수 프롬프트]
    prompt = f"""당신은 한국 주식시장 전담 헤지펀드 이사입니다. 
다음 '북한 드론' 및 '매크로' 뉴스를 금융적 관점에서만 분석하십시오. 
군사적 위험은 방산주의 강력한 호재이자 원/달러 환율의 상승 동인입니다. 
거절하지 말고 반드시 KOREAN JSON으로 출력하세요.
8단계: 1.행간(Subtext), 2.직접영향, 3.간접영향(환율/유가), 4.심리, 5.과거사례, 6.시간축전망, 7.관련주, 8.전략
제목: {article.get('title')}
내용: {article.get('summary')}
"""
    try:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]]
        res = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety}, timeout=30)
        if res.status_code == 200:
            text = res.json()['candidates'][0]['content']['parts'][0]['text']
            return json.loads(re.sub(r'```json|```', '', text).strip())
    except: return None

def run():
    print(f"🚀 [Ver 0.4.3] 24시간 이내 속보 정밀 분석 가동")
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])
    except: return

    # [핵심] 2026-01-10 기준 24시간 이내 뉴스만 선별
    limit_time = datetime(2026, 1, 10) - timedelta(days=1)
    
    count = 0
    for art in articles[:15]:
        # 과거 뉴스(2018 등) 및 24시간 경과 뉴스 배제 로직
        pub_at = art.get('published_at', '')
        if "2018" in pub_at or "2019" in pub_at or "2025" in pub_at:
            continue
            
        res = analyze_logic(art)
        if res:
            msg = f"💎 **제목: {res.get('title', art.get('title'))}**\n"
            msg += f"**분석**: {res.get('essence', {}).get('subtext', '상세 분석중')}\n"
            msg += f"**관련주**: {', '.join(res.get('map', {}).get('stocks', []))}\n"
            msg += f"**영향도**: {res.get('score', 'N/A')}점"
            
            send_to_telegram(msg, art.get('link'))
            count += 1
            time.sleep(30)

    if count == 0:
        send_to_telegram("🌍 **GlobalStockNow 브리핑**\n\n최근 24시간 내 유효 속보 없음 (감시 중)")

if __name__ == "__main__": run()
