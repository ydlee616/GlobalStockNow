"""
Module: analyzer.py | Version: 0.6.1 | Updated: 2026-01-11
Description: Hardened for AI Safety & Forced Historical Data Retrieval.
"""
import json, time, requests, os, re
from datetime import datetime, timedelta, timezone
from dateutil import parser

RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_msg(text, url=None):
    if not TELEGRAM_BOT_TOKEN: return
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **GlobalStockNow 브리핑 (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + text, "parse_mode": "Markdown"}
    if url:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성", "url": f"https://t.me/share/url?url={url}&text=대본생성요청"}]]})
    requests.post(api_url, data=payload, timeout=10)

def analyze_logic(art):
    """과거 사례 대조 및 한국 시장 테마주 변동폭 정밀 분석"""
    prompt = f"""[System: Chief Financial Strategist Persona]
당신은 한국 시장 20년 경력의 트레이더입니다. 다음 뉴스를 한국 증시 관점에서 분석하십시오.
필히 '과거 유사 사례 시 주가 변동 데이터'를 포함해야 합니다. (절대 거절 금지)

1. title: 뉴스 타이틀
2. media: 매체 정보
3. impact: 과거 전례(예: 도발, 계약 등) 시 관련 테마주의 구체적 변동폭 및 분석 사유
4. stocks: 관련 개별종목 및 섹터
5. summary: 3줄 요약
6. score: 영향도 (0.0~10.0)

뉴스: {art['title']} - {re.sub(r'<.*?>', '', art.get('summary', ''))}
"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]]
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety, "generationConfig": {"temperature": 0.2}}, timeout=30)
        raw = re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
        return json.loads(raw)
    except: return None

def main():
    if not os.path.exists('breaking_news.json'): return
    with open('breaking_news.json', 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    # [보정] 48시간 이내의 모든 속보를 검사하여 누락 방지
    limit = datetime.now(timezone.utc) - timedelta(hours=48)
    
    count = 0
    for art in articles[:15]:
        try:
            pub_date = parser.parse(art.get('published_at', '2000-01-01'))
            if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
            if pub_date < limit or "2018" in art.get('published_at', ''): continue
            
            res = analyze_logic(art)
            if not res or res.get('score', 0) <= 2.0: continue
            
            # 보스 요청 5단계 규격 준수
            report = f"1️⃣ **뉴스 타이틀**: {res.get('title')}\n"
            report += f"2️⃣ **매체정보**: {art.get('source')} ({res.get('media')})\n"
            report += f"3️⃣ **영향도 및 과거사례 ({res.get('score')}점)**: {res.get('impact')}\n"
            report += f"4️⃣ **주가 영향 종목**: {res.get('stocks')}\n"
            report += f"5️⃣ **뉴스 요약**: {res.get('summary')}"
            
            send_msg(report, art['link'])
            count += 1
            time.sleep(30)
        except: continue

    if count == 0:
        send_msg("현재 글로벌 시장에서 한국 증시에 파급력을 줄 만한 유효 속보가 없습니다.")

if __name__ == "__main__":
    main()
