"""Module: analyzer.py | Version: 0.4.0 | Updated: 2026-01-10"""
import json, time, requests, os, re
from datetime import datetime

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")

def send_to_telegram(msg, article_url=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    
    # [핵심 수정] 버튼을 보스가 선택할 수 있도록 인라인 키보드 강제 부착
    if article_url:
        payload["reply_markup"] = json.dumps({
            "inline_keyboard": [[
                {"text": "🎬 유튜브 시나리오 생성 (학습)", "url": f"https://t.me/share/url?url={article_url}&text=유튜브대본생성요청"}
            ]]
        })
    requests.post(url, data=payload, timeout=10)

def analyze_core(article):
    # 세이프티 필터 우회를 위한 강화된 프롬프트
    prompt = f"""[Strategic Financial Analyst Persona]
Analyze this news for South Korean Stock Market impact. Be bold and deep.
1.Essence, 2.Direct, 3.Indirect(FX/Commodities), 4.Sentiment, 5.History, 6.Timeline, 7.Sectors/Stocks, 8.Strategy
News: {article.get('title')}
Output KOREAN JSON ONLY."""
    
    try:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]]
        res = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety, "generationConfig": {"temperature": 0.3}}, timeout=30)
        if res.status_code == 200:
            text = res.json()['candidates'][0]['content']['parts'][0]['text']
            return json.loads(re.sub(r'```json|```', '', text).strip())
    except: return None

def run():
    print(f"🚀 [Ver 0.4.0] 정밀 분석 가동...")
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])
    except: return

    count = 0
    for art in articles[:12]:
        if any(y in art.get('published_at', '') for y in ['2018', '2019']): continue
        
        res = analyze_core(art)
        if res:
            # 5단계 리포트 구성 (보스 요청 양식) [cite: 2026-01-09]
            msg = f"💎 **1. 제목: {res.get('title', art.get('title'))}**\n"
            msg += f"**2. 매체**: {art.get('source')}\n"
            msg += f"**3. 영향 ({res.get('score', 0)}점)**: {res.get('essence', {}).get('subtext', '분석중')}\n"
            msg += f"**4. 관련주**: {', '.join(res.get('map', {}).get('stocks', []))}\n"
            msg += f"**5. 과거사례**: {res.get('history', {}).get('case', 'N/A')}"
            
            # [버튼 포함 발송]
            send_to_telegram(msg, art.get('link'))
            count += 1
            time.sleep(32)

    if count == 0:
        send_to_telegram(f"🌍 **GlobalStockNow 브리핑 (#{RUN_NUMBER})**\n\n특이사항 없음. 감시 중.")

if __name__ == "__main__": run()
