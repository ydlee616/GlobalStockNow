"""Module: analyzer.py | Version: 1.6.6 | Focus: Pre-Analysis & Summary Cleaning"""
import json, time, requests, os, re

BRAND_NAME = "GlobalStockNow 브리핑"
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_boss_with_buttons(msg, link, news_id):
    """지시하신 5대 항목과 버튼 전송"""
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔗 뉴스 원문 보기", "url": link}],
            [{"text": "📝 블로그 초안 생성 (The Specialist)", "callback_data": f"draft_{news_id}"}]
        ]
    }
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "reply_markup": json.dumps(keyboard)}
    requests.post(url, data=payload, timeout=10)

def analyze_basic_fields(art):
    """[신규] 텔레그램 보고용 5대 항목 사전 분석 엔진"""
    prompt = f"""당신은 한국 금융 전문가입니다. 다음 뉴스를 분석하여 텔레그램 리포트용 JSON을 만드세요.
1. title: 한글 뉴스 제목
2. source: 뉴스 매체명 (영어)
3. impact: 주가 영향도 점수(0-10)와 짧은 사유 (한글)
4. stocks: 국내 관련 상장주 및 테마군 (한글)
5. summary: 군더더기 없는 한글 요약 (한글)

뉴스 원문: {art['title']}
JSON 형식으로만 답변하세요."""

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=data, timeout=30)
        return json.loads(res.json()['choices'][0]['message']['content'])
    except: return None

def main():
    print(f"🚀 [Ver 1.6.6] {RUN_NUMBER} 파이프라인 사전 분석 모드 가동")
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        for i, art in enumerate(articles[:10]):
            # 5대 항목 사전 분석 수행
            analysis = analyze_basic_fields(art)
            if not analysis: continue

            # [보스 지시사항] 5대 기본 항목 형식 엄격 고정
            report_msg = (f"🌍 **{BRAND_NAME} (#{RUN_NUMBER})**\n\n"
                          f"1️⃣ **뉴스 제목**: {analysis.get('title')}\n"
                          f"2️⃣ **출처 (Source)**: {analysis.get('source')}\n"
                          f"3️⃣ **주가 영향도**: {analysis.get('impact')}\n"
                          f"4️⃣ **관련 종목/테마**: {analysis.get('stocks')}\n"
                          f"5️⃣ **뉴스 요약**: {analysis.get('summary')}")
            
            send_to_boss_with_buttons(report_msg, art['link'], i)
            time.sleep(1)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__": main()
