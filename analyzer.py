"""Module: analyzer.py | Version: 1.4.0 | Focus: K-Stock Mapping & Localization"""
import json, time, requests, os, re

BRAND_NAME = "GlobalStockNow 브리핑"
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_boss(msg, link=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **{BRAND_NAME} (#{RUN_NUMBER})**\n\n"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + msg, "parse_mode": "Markdown"}
    if link:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성", "url": f"https://t.me/share/url?url={link}&text=시나리오요청"}]]})
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def analyze_with_groq(art):
    """[Fix] 한국어 출력 및 국내 상장주 매핑 로직 강화"""
    # 프롬프트에 '한국어 출력'과 '국내 관련주 매핑'을 강력하게 명령합니다.
    prompt = f"""당신은 월스트리트 출신의 한국 증시 전문가입니다. 
다음 글로벌 뉴스가 한국 코스피/코스닥 시장에 미치는 영향을 분석하고, 반드시 '한국어'로 JSON 결과를 출력하세요.

[분석 가이드라인]:
1. 제목(title): 한국 투자자가 이해하기 쉬운 명확한 한글 제목으로 번역.
2. 영향도(impact): 해당 기술/정책이 한국의 산업 밸류체인(삼성, 하이닉스, 현대차 등)에 미치는 구체적 영향을 분석.
3. 관련주(stocks): 해당 뉴스와 직결되는 '대한민국 상장 기업'의 이름을 명시 (예: 두산에너빌리티, 한미반도체 등).
4. 요약(summary): 핵심 내용 3줄 요약.
5. 점수(score): 투자 시급성에 따른 0~10점 척도.

뉴스 원문: {art['title']}
JSON 형식으로만 답변하세요."""

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        data = {
            "model": "llama-3.3-70b-versatile", 
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=data, timeout=30)
        
        if res.status_code != 200:
            return {"error": f"API {res.status_code}"}
            
        return json.loads(res.json()['choices'][0]['message']['content'])
    except Exception as e:
        return {"error": "분석 오류"}

def main():
    send_to_boss("🚀 **K-Stock 매핑 엔진(v1.4.0) 가동**\n글로벌 시그널을 국내 수익 기회로 치환합니다.")
    
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        report_count = 0
        inspected_list = []

        for art in articles[:15]:
            res = analyze_with_groq(art)
            
            if res and "error" in res:
                inspected_list.append(f"• [⚠] {res['error']} | {art['title'][:20]}...")
                continue

            score = float(res.get('score', 0)) if res else 0
            inspected_list.append(f"• [{score}점] {res.get('title', '제목없음')[:30]}...")

            # 2.0점 이상이면 상세 리포트 발송
            if res and score > 2.0:
                report = (f"📍 **뉴스**: {res.get('title')}\n"
                          f"🔥 **투자 전략 ({score}점)**: {res.get('impact')}\n"
                          f"✅ **국내 관련주**: {res.get('stocks')}\n"
                          f"📝 **핵심 요약**: {res.get('summary')}")
                send_to_boss(report, art['link'])
                report_count += 1
                time.sleep(1)

        summary = f"✅ **K-파이프라인 가동 완료**\n- 분석: {len(articles)}건 / 리포트: {report_count}건\n\n"
        summary += "**[실시간 국내주 가치 평가]**\n" + "\n".join(inspected_list[:15])
        send_to_boss(summary)

    except Exception as e:
        send_to_boss(f"❌ **시스템 오류**: {str(e)}")

if __name__ == "__main__": main()
