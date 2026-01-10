"""
Module: analyzer.py | Version: 0.4.7 | Updated: 2026-01-11
Description: Hardened Error Handling & Mandatory Button Output.
"""
import json, time, requests, os, re
from datetime import datetime, timedelta, timezone
from dateutil import parser

# 전역 변수 - 메시지 어디서든 파이프라인 번호 확인 가능하게 고정
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_final_report(content, link=None):
    """보스의 디버깅을 위해 파이프라인 번호를 메시지 최상단에 고정 발송"""
    if not TELEGRAM_BOT_TOKEN: return
    header = f"🌍 **GlobalStockNow 브리핑 (#{RUN_NUMBER})**\n\n"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + content, "parse_mode": "Markdown"}
    
    if link: # 기사가 있다면 무조건 버튼 부착
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 대본 제작 선택", "url": f"https://t.me/share/url?url={link}&text=유튜브대본생성요청"}]]})
    try: requests.post(url, data=payload, timeout=10)
    except: print("Telegram Send Failed")

def clean_summary(raw_text):
    """HTML 태그 제거로 AI 혼선 방지"""
    return re.sub(r'<.*?>', '', raw_text) if raw_text else ""

def call_ai(art):
    """안보 이슈를 금융으로 치환하는 특수 프롬프트"""
    clean_text = clean_summary(art.get('summary', ''))
    p = f"[Director Mode] Analyze impact on KOSPI/KOSDAQ. Output KOREAN JSON.\nNews: {art['title']} - {clean_text}"
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]]
        res = requests.post(url, json={"contents": [{"parts": [{"text": p}]}], "safetySettings": safety}, timeout=30)
        # JSON 파싱 실패 대비 안전 장치
        raw_res = re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
        return json.loads(raw_res)
    except Exception as e:
        print(f"AI 호출 오류: {e}")
        return None

def main():
    print(f"🚀 Ver 0.4.7 가동 - 파이프라인 #{RUN_NUMBER}")
    if not os.path.exists('breaking_news.json'): return
    
    with open('breaking_news.json', 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    # 24시간 속보 기준 설정 (타임존 인식)
    now = datetime.now(timezone.utc)
    limit = now - timedelta(hours=24)
    
    success_count = 0
    for art in articles[:15]:
        try:
            # 1. 과거 쓰레기 데이터 필터링
            pub_date = parser.parse(art.get('published_at', '2000-01-01'))
            if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
            if pub_date < limit or "2018" in art.get('published_at', ''): continue
            
            # 2. AI 분석
            res = call_ai(art)
            
            # 3. 결과 발송 (데이터 누락 시 기본값 채우기)
            title = res.get('title', art['title']) if res else art['title']
            subtext = res.get('essence', {}).get('subtext', 'AI 분석 완료') if res else '분석 엔진 일시 지연'
            score = res.get('score', 0) if res else 0
            
            msg = f"💎 **제목: {title}**\n**점수**: {score}점\n**행간**: {subtext}"
            send_final_report(msg, art['link'])
            success_count += 1
            time.sleep(32) # Rate Limit 방지
        except Exception as e:
            print(f"개별 기사 분석 중 에러(스킵): {e}")
            continue

    if success_count == 0:
        send_final_report("현재 24시간 내 유효 속보 없음 (정밀 감시 중)")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        # 최후의 보루: 메인 루프가 터져도 보스께 번호를 알림
        send_final_report(f"⚠️ 시스템 치명적 오류 발생: {e}")
