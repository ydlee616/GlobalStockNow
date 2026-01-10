"""Module: analyzer.py | Version: 1.0.4 | Visionary: Steve Jobs Concept"""
import json, time, requests, os, re

# ==========================================
# [BRANDING] 절대 불변의 상수
# ==========================================
BRAND_NAME = "GlobalStockNow 브리핑"

# 환경 변수
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def report_to_boss(msg, link=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **{BRAND_NAME} (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + msg, "parse_mode": "Markdown"}
    if link:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성", "url": f"https://t.me/share/url?url={link}&text=시나리오요청"}]]})
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def analyze_strategic(art):
    """8단계 정밀 분석 프롬프트 (안보 뉴스를 금융 데이터로 치환)"""
    prompt = f"""당신은 한국 시장 특화 CIO입니다. 다음 뉴스를 과거 유사 사례와 비교 분석하십시오.
특히 북한 관련 안보 리스크는 과거 주가 변동 데이터를 필히 소환할 것.

[출력 JSON 규격]:
{{
  "title": "뉴스 타이틀",
  "media": "매체 정보",
  "impact": "과거 전례 대비 영향도 정밀 분석",
  "stocks": "주가 영향 종목 및 섹터",
  "summary": "3줄 요약",
  "score": 0.0
}}

뉴스: {art['title']}"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]}, timeout=30)
        raw = re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
        return json.loads(raw)
    except: return None

def main():
    # 1. Heartbeat 시작 보고 (침묵 금지)
    report_to_boss("🚀 **분석 엔진 가동 시작**\n글로벌 밸류체인 48h 정밀 분석을 개시합니다.")
    
    try:
        if not os.path.exists('breaking_news.json'): return
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        report_count = 0
        for art in articles[:10]:
            # [Fix #188] 루프 시작 시 res 변수 초기화
            res = None
            res = analyze_strategic(art)
            
            # 2.0점 초과 뉴스만 정예 보고
            if res and float(res.get('score', 0)) > 2.0:
                msg = (f"1️⃣ **뉴스 타이틀**: {res.get('title')}\n"
                       f"2️⃣ **매체정보**: {art.get('source')} ({res.get('media', '외신')})\n"
                       f"3️⃣ **영향도 및 과거분석 ({res.get('score')}점)**: {res.get('impact')}\n"
                       f"4️⃣ **주가 영향 종목**: {res.get('stocks')}\n"
                       f"5️⃣ **뉴스 요약**: {res.get('summary')}")
                report_to_boss(msg, art['link'])
                report_count += 1
                time.sleep(30) # Rate Limit 방어

        # 2. 최종 요약 보고 (침묵의 시대 종결)
        status = f"✅ **파이프라인 프로세스 완료**\n- 검토: {len(articles)}건\n- 보고: {report_count}건"
        if report_count == 0:
            status += "\n- 특이사항: 현재 고영향도(2.0점 초과) 속보가 발견되지 않았습니다."
        report_to_boss(status)

    except Exception as e:
        report_to_boss(f"❌ **내부 시스템 치명적 오류**: {str(e)}")

if __name__ == "__main__": main()
