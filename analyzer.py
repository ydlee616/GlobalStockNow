"""
Module: analyzer.py | Version: 0.5.1 | Updated: 2026-01-11
Description: Internal Historical Case Study & Themed Stock Price Action Analysis.
"""
import json, time, requests, os, re
from datetime import datetime, timedelta, timezone
from dateutil import parser

RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_telegram(report, url=None):
    if not TELEGRAM_BOT_TOKEN: return
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **GlobalStockNow 브리핑 (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + report, "parse_mode": "Markdown"}
    if url:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성 (학습)", "url": f"https://t.me/share/url?url={url}&text=유튜브대본생성요청"}]]})
    requests.post(api_url, data=payload, timeout=10)

def analyze_historical(art):
    """과거 동일 사례의 주가 변동 데이터를 소환하여 분석"""
    prompt = f"""당신은 한국 시장 20년 경력의 헤지펀드 트레이더입니다. 
다음 북한/안보 뉴스를 분석하되, 반드시 '과거 유사 사례'와 '테마주 변동 내역'을 포함하십시오.

[분석 지침]:
1. 과거 이와 유사한 북한 도발(무인기, 미사일, 포격 등) 시 방산주(빅텍, LIG넥스원, 한화에어로 등)가 평균적으로 몇 % 상승했었는지 소환할 것.
2. 당시 주가가 며칠 만에 고점을 찍고 반락했는지 패턴을 분석할 것.
3. 현재 상황이 과거 패턴과 일치하는지, 아니면 새로운 국면인지 판별할 것.

[출력 JSON 규격]:
{{
  "title": "뉴스 타이틀",
  "media": "매체 정보",
  "impact": "영향도 및 과거 전례 대비 분석 (과거 주가 데이터 포함)",
  "stocks": "주가 영향 테마주/개별종목 및 예상 변동폭",
  "summary": "뉴스 핵심 요약",
  "score": 0.0
}}

뉴스: {art['title']} - {re.sub(r'<.*?>', '', art.get('summary', ''))}
"""
    try:
        api = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]]
        res = requests.post(api, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety, "generationConfig": {"temperature": 0.2}}, timeout=30)
        raw_json = re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
        return json.loads(raw_json)
    except: return None

def main():
    if not os.path.exists('breaking_news.json'): return
    with open('breaking_news.json', 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    # 보스, 2026년 1월 10일 뉴스를 놓치지 않도록 36시간 필터를 유지합니다.
    limit = datetime.now(timezone.utc) - timedelta(hours=36)
    
    count = 0
    for art in articles[:15]:
        try:
            pub_date = parser.parse(art.get('published_at', '2000-01-01'))
            if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
            if pub_date < limit or "2018" in art.get('published_at', ''): continue
            
            res = analyze_historical(art)
            
            # 보스, 2점 이하 뉴스는 텔레그램을 어지럽히므로 스킵합니다.
            if not res or res.get('score', 0) <= 2.0: continue
            
            # [복구] 보스 요청 5단계 리포트 양식
            report = f"1️⃣ **뉴스 타이틀**: {res.get('title')}\n"
            report += f"2️⃣ **매체정보**: {art.get('source')} ({res.get('media')})\n"
            report += f"3️⃣ **영향도 및 과거사례 분석 ({res.get('score')}점)**: {res.get('impact')}\n"
            report += f"4️⃣ **주가 영향 테마주**: {res.get('stocks')}\n"
            report += f"5️⃣ **뉴스 요약**: {res.get('summary')}"
            
            send_to_telegram(report, art['link'])
            count += 1
            time.sleep(32)
        except: continue

    if count == 0:
        send_to_telegram("현재 전략적으로 분석 가치가 있는 (2.0점 초과) 북한/글로벌 속보가 없습니다.")

if __name__ == "__main__":
    main()
