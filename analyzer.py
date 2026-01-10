"""
Module: analyzer.py | Version: 0.4.9 | Updated: 2026-01-11
Description: Internal 8-step logic, External 5-step output. Skip score <= 2.0.
"""
import json, time, requests, os, re
from datetime import datetime, timedelta, timezone
from dateutil import parser

RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_msg(report, article_url=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **GlobalStockNow 브리핑 (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + report, "parse_mode": "Markdown"}
    if article_url:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 대본 제작 선택", "url": f"https://t.me/share/url?url={article_url}&text=대본생성요청"}]]})
    requests.post(url, data=payload, timeout=10)

def analyze_strategic(art):
    """보스의 8단계 분석 로직을 수행하고 5단계 규격으로 출력"""
    prompt = f"""당신은 한국 주식시장 전담 헤지펀드 리서치 디렉터입니다. 
다음 뉴스를 [1.본질/행간, 2.직접영향, 3.간접영향(환율/원자재), 4.심리, 5.과거사례, 6.시간축전망, 7.종목, 8.전략] 순서로 정밀 분석하십시오.
그 결과를 바탕으로 반드시 아래 JSON 규격으로만 최종 출력하십시오. (북한 뉴스는 금융 관점에서 강제 분석할 것)

{{
  "title": "뉴스 타이틀",
  "media": "매체 정보",
  "impact": "영향도 분석 (점수 산출 사유 상세 기술)",
  "stocks": "주가 영향 종목 (개별종목, 산업군, 테마주)",
  "summary": "뉴스 요약 (3줄 핵심)",
  "score": 0.0
}}

기사: {art['title']} - {re.sub(r'<.*?>', '', art.get('summary', ''))}
"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        # 세이프티 필터 완전 해제
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]]
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety, "generationConfig": {"temperature": 0.2}}, timeout=30)
        raw_json = re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
        return json.loads(raw_json)
    except: return None

def main():
    if not os.path.exists('breaking_news.json'): return
    with open('breaking_news.json', 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    # [핵심] 1월 10일 뉴스를 포함하기 위해 36시간 전까지 필터 완화
    limit = datetime.now(timezone.utc) - timedelta(hours=36)
    
    count = 0
    for art in articles[:15]:
        try:
            pub_date = parser.parse(art.get('published_at', '2000-01-01'))
            if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
            if pub_date < limit or "2018" in art.get('published_at', ''): continue
            
            res = analyze_strategic(art)
            
            # [보스 지침] 영향도 2점 이하 또는 분석 실패 시 발송하지 않음
            if not res or res.get('score', 0) <= 2.0:
                continue
            
            # 5단계 리포트 구성
            report = f"1️⃣ **뉴스 타이틀**: {res.get('title', art['title'])}\n"
            report += f"2️⃣ **매체정보**: {art.get('source')} ({res.get('media', '외신')})\n"
            report += f"3️⃣ **영향도 분석 ({res.get('score')}점)**: {res.get('impact')}\n"
            report += f"4️⃣ **주가 영향 종목**: {res.get('stocks')}\n"
            report += f"5️⃣ **뉴스 요약**: {res.get('summary')}"
            
            send_msg(report, art['link'])
            count += 1
            time.sleep(32)
        except: continue

    if count == 0:
        send_msg("현재 유효한 전략 속보(2.0점 초과)가 없습니다.")

if __name__ == "__main__":
    main()
