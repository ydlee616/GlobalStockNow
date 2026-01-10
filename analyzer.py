"""Module: analyzer.py | Version: 1.6.0 | Focus: Historical Analogy & Future Forecasting"""
import json, time, requests, os, re

BRAND_NAME = "GlobalStockNow 브리핑"
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_boss(msg, link=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True}
    if link:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🔗 뉴스 원문 보기", "url": link}]]})
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def analyze_full_spectrum(art):
    """[핵심] 과거 사례 분석 및 미래 주가 변동성 예측 로직"""
    prompt = f"""당신은 20년 경력의 수석 퀀트 애널리스트입니다. 
다음 뉴스를 과거 시장 데이터와 대조하여 한국 증시의 미래를 예측하고 JSON으로 답변하세요.

[필수 분석 항목]:
1. title: 한국어 제목
2. historical_case: 이 뉴스와 가장 유사했던 '과거의 사건'과 당시 한국 증시(종목명 포함)의 구체적 변동 수치/패턴 기술.
3. impact: 현재 시점에서의 한국 공급망 영향력 분석.
4. stocks: 국내 핵심 수혜주 리스트.
5. future_forecast: 향후 1주일~1개월간의 예상 주가 변동 방향 및 변동폭($\pm\%$) 평가.
6. shorts_script: 시청자를 압도하는 전문적이고 속도감 있는 쇼츠 대본.
7. score: 0~10점 (투자 매력도).

뉴스: {art['title']}
반드시 JSON 형식으로만 답변하세요."""

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.3-70b-versatile", 
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=data, timeout=30)
        return json.loads(res.json()['choices'][0]['message']['content'])
    except: return None

def main():
    send_to_boss(f"🚀 **타임라인 인텔리전스(v1.6.0) 가동**\n과거 패턴 분석 및 미래 변동성 평가를 수행합니다.")
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        for art in articles[:10]:
            res = analyze_full_spectrum(art)
            if not res: continue
            
            score = float(res.get('score', 0))
            if score >= 6.5: # 보스, 분석의 깊이가 깊어진 만큼 기준을 6.5로 정교화했습니다.
                # 1. 딥 전략 리포트 (과거 및 미래 포함)
                report = (f"🌍 **{BRAND_NAME} (#{RUN_NUMBER})**\n\n"
                          f"📍 **뉴스**: {res.get('title')}\n\n"
                          f"🕰 **과거 유사 사례**: {res.get('historical_case')}\n\n"
                          f"🔥 **현시점 임팩트**: {res.get('impact')}\n\n"
                          f"✅ **관련 종목**: {res.get('stocks')}\n\n"
                          f"📈 **미래 변동 예측**: {res.get('future_forecast')}\n\n"
                          f"⭐ **종합 점수**: {score}/10")
                send_to_boss(report, art['link'])
                
                # 2. 쇼츠 시나리오 (복사용)
                time.sleep(1)
                script_msg = f"🎬 **[고품질 쇼츠 시나리오]**\n\n{res.get('shorts_script')}"
                send_to_boss(script_msg)
                
                time.sleep(2)

    except Exception as e:
        send_to_boss(f"❌ 분석 엔진 중단: {str(e)}")

if __name__ == "__main__": main()
