"""
Module: analyzer.py | Version: 0.4.1 | Updated: 2026-01-11
Description: Guaranteed Button visibility & HTML data cleaning.
"""
import json, time, requests, os, re
from datetime import datetime

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")

def clean_html(text):
    return re.sub(r'<.*?>', '', text) if text else ""

def send_telegram_with_button(msg, article_url):
    """보스의 선별을 위해 버튼을 100% 확률로 포함하여 발송"""
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # 보스가 바로 선택할 수 있도록 텔레그램 공유 링크 방식으로 버튼 구현
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps({
            "inline_keyboard": [[
                {"text": "🎬 이 뉴스로 유튜브 시나리오 생성 요청", "url": f"https://t.me/share/url?url={article_url}&text=유튜브대본생성"}
            ]]
        })
    }
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def analyze_core(article):
    # [cite: 2026-01-09] 보강된 8단계 정밀 분석 프롬프트
    prompt = f"""[Strategic Financial Analyst Mode]
Analyze the following news for South Korean Market impact. Be bold.
1.Essence(Subtext), 2.Direct, 3.Indirect(FX/Commodities), 4.Sentiment, 5.History, 6.Timeline, 7.Sectors/Stocks, 8.Strategy
News: {article.get('title')} - {clean_html(article.get('summary'))}
Output KOREAN JSON ONLY."""

    try:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]]
        res = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety, "generationConfig": {"temperature": 0.2}}, timeout=30)
        if res.status_code == 200:
            text = res.json()['candidates'][0]['content']['parts'][0]['text']
            return json.loads(re.sub(r'```json|```', '', text).strip())
    except: return None

def run():
    print(f"🚀 [Ver 0.4.1] 정밀 분석 및 인터랙티브 인터페이스 가동")
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])
    except: return

    count = 0
    # 최신 뉴스 중 상위 12개를 엄선하여 분석
    for art in articles[:12]:
        # 과거 기사 필터링 (2018, 2019)
        if any(y in art.get('published_at', '') for y in ['2018', '2019']): continue
        
        res = analyze_core(art)
        if res:
            # 보스 요청 5단계 리포트 양식 [cite: 2026-01-09]
            msg = f"💎 **1. 제목: {res.get('title', art.get('title'))}**\n"
            msg += f"**2. 매체정보**: {art.get('source')}\n"
            msg += f"**3. 영향도 ({res.get('score', 0)}점)**: {res.get('essence', {}).get('subtext', '행간 분석 완료')}\n"
            msg += f"**4. 영향받는 주식**: {', '.join(res.get('map', {}).get('stocks', []))}\n"
            msg += f"**5. 과거사례**: {res.get('history', {}).get('case', '유사 사례 분석중')}\n"
            msg += f"----------------------------\n"
            msg += f"💡 **전략**: {res.get('strategy', {}).get('action', '관망')}"
            
            send_telegram_with_button(msg, art.get('link'))
            count += 1
            time.sleep(32)

    if count == 0:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": f"🌍 **GlobalStockNow 브리핑 (#{RUN_NUMBER})**\n\n현재 유효 속보 없음 (정밀 감시 중)"})

if __name__ == "__main__": run()
