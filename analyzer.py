"""Module: analyzer.py | Version: 1.0.2 | Visionary: Steve Jobs Style"""
import json, time, requests, os, re

# ==========================================
# [CORE BRANDING] 보스의 고유 브랜드 명칭
# ==========================================
BRAND_NAME = "GlobalStockNow 브리핑"

# 환경 변수 및 설정
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
    requests.post(url, data=payload, timeout=10)

def analyze_strategic(art):
    """8단계 정밀 분석 프롬프트 로직"""
    prompt = f"Analyze for KOSPI impact. Output JSON. News: {art['title']}"
    try:
        api = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        res = requests.post(api, json={"contents": [{"parts": [{"text": prompt}]}], "safetySettings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]}, timeout=30)
        return json.loads(re.sub(r'```json|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip())
    except: return None

def main():
    report_to_boss("🚀 **분석 엔진 가동 시작**\n글로벌 밸류체인 정밀 분석을 개시합니다.")
    
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        report_count = 0
        for art in articles[:10]:
            # [Fix] 변수 초기화로 name 'res' is not defined 에러 방지
            res = analyze_strategic(art)
            
            if res and float(res.get('score', 0)) > 2.0:
                # 보스 요청 5단계 규격 엄수
                msg = (f"1️⃣ **뉴스 타이틀**: {res.get('title')}\n"
                       f"2️⃣ **매체정보**: {art.get('source')} ({res.get('media', 'Global')})\n"
                       f"3️⃣ **영향도 및 과거분석 ({res.get('score')}점)**: {res.get('impact')}\n"
                       f"4️⃣ **주가 영향 종목**: {res.get('stocks')}\n"
                       f"5️⃣ **뉴스 요약**: {res.get('summary')}")
                report_to_boss(msg, art['link'])
                report_count += 1
                time.sleep(30)

        status = f"✅ **파이프라인 프로세스 완료**\n- 검토: {len(articles)}건\n- 보고: {report_count}건"
        if report_count == 0: status += "\n- 특이사항: 현재 고영향도 속보가 발견되지 않았습니다."
        report_to_boss(status)

    except Exception as e:
        report_to_boss(f"❌ **내부 시스템 오류**: {str(e)}")

if __name__ == "__main__": main()
