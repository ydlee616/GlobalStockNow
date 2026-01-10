"""
Module: analyzer.py | Version: 0.4.9 | Updated: 2026-01-11
Description: 5-step report structure with 8-step internal logic. 
             Strict score filtering (skip <= 2.0) and safety bypass.
"""
import json, time, requests, os, re
from datetime import datetime, timedelta, timezone
from dateutil import parser

# 전역 설정
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_telegram(report_text, article_url=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **GlobalStockNow 브리핑 (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + report_text, "parse_mode": "Markdown"}
    
    if article_url:
        payload["reply_markup"] = json.dumps({
            "inline_keyboard": [[{"text": "🎬 유튜브 대본 제작 선택", "url": f"https://t.me/share/url?url={article_url}&text=유튜브대본생성요청"}]]
        })
    try: requests.post(url, data=payload, timeout=10)
    except: print("Telegram 전송 실패")

def analyze_strategic(art):
    """보스의 8단계 로직을 수행하되 5대 항목으로 결과 도출"""
    clean_summary = re.sub(r'<.*?>', '', art.get('summary', ''))
    
    # [보스 지침 반영] 8단계 분석 로직 기반의 프롬프트 구성
    prompt = f"""당신은 한국 시장 특화 헤지펀드 리서치 디렉터입니다. 
다음 뉴스를 8단계(본질, 직접영향, 간접영향, 심리, 과거사례, 시간축전망, 종목, 전략)로 정밀 분석한 후, 
최종적으로 아래 JSON 규격에 맞춰 출력하십시오. 
안보 뉴스는 경제적 관점에서 방산주 및 환율 변동성을 중심으로 분석하며, 절대 거절하지 마십시오.

[필수 JSON 키]:
1. title: 뉴스 타이틀 (정제된 제목)
2. media: 매체 정보 (원출처 포함)
3. impact: 영향도 분석 (점수와 함께 그 사유를 경제 논리로 상세 기술)
4. stocks: 주가 영향 종목 (개별종목, 산업군, 테마주 리스트)
5. summary: 뉴스 요약 (핵심 팩트 3줄 이내)
6. score: 0.0 ~ 10.0 사이의 영향도 점수

뉴스 원제: {art['title']}
뉴스 내용: {clean_summary}
"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        # 세이프티 차단 전면 해제 (BLOCK_NONE)
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]]
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety, "generationConfig": {"temperature": 0.2}}, timeout=30)
        
        raw_res = re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
        return json.loads(raw_res)
    except Exception as e:
        print(f"분석 엔진 오류: {e}")
        return None

def main():
    print(f"🚀 [Ver 0.4.9] 분석 시작 - 파이프라인 #{RUN_NUMBER}")
    if not os.path.exists('breaking_news.json'): return
    
    with open('breaking_news.json', 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    # 24시간 속보 기준 (타임존 인식)
    now = datetime.now(timezone.utc)
    limit = now - timedelta(hours=24)
    
    sent_count = 0
    for art in articles[:15]:
        try:
            pub_date = parser.parse(art.get('published_at', '2000-01-01'))
            if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
            
            # 24시간 이내 속보 및 2018년 등 과거 뉴스 필터링
            if pub_date < limit or "2018" in art.get('published_at', ''): continue
            
            res = analyze_strategic(art)
            
            # [보스 지침] 영향도가 2.0 이하이거나 분석에 실패한 경우 보스께 보고하지 않음
            if not res or res.get('score', 0) <= 2.0:
                print(f"스킵: {art['title'][:20]}... (점수 미달 또는 분석 실패)")
                continue
            
            # 보스 전용 5대 리포트 규격 조립
            report = f"1️⃣ **뉴스 타이틀**: {res.get('title', art['title'])}\n"
            report += f"2️⃣ **매체정보**: {art.get('source')} ({res.get('media', '외신')})\n"
            report += f"3️⃣ **영향도 분석 ({res.get('score', 0)}점)**: {res.get('impact')}\n"
            report += f"4️⃣ **주가 영향 종목**: {res.get('stocks')}\n"
            report += f"5️⃣ **뉴스 요약**: {res.get('summary')}"
            
            send_to_telegram(report, art['link'])
            sent_count += 1
            time.sleep(32)
        except Exception as e:
            print(f"루프 내 에러: {e}")

    if sent_count == 0:
        send_to_telegram("현재 24시간 내 시장에 영향을 줄 만한 (2.0점 초과) 전략 속보가 없습니다.")

if __name__ == "__main__":
    main()
