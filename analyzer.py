"""Module: analyzer.py | Version: 1.5.0 | Focus: YouTube Shorts Script Generation"""
import json, time, requests, os, re

BRAND_NAME = "GlobalStockNow 브리핑"
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_boss(msg, link=None, scenario=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    header = f"🌍 **{BRAND_NAME} (#{RUN_NUMBER})**\n\n"
    
    # 시나리오가 있을 경우 메시지에 포함하거나 버튼으로 연결
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": header + msg, "parse_mode": "Markdown"}
    
    keyboard = []
    if link:
        keyboard.append([{"text": "🔗 뉴스 원문 보기", "url": link}])
    if scenario:
        # 텔레그램의 데이터 길이 제한으로 인해 시나리오는 별도 메시지로 보낼 준비
        keyboard.append([{"text": "🎬 유튜브 시나리오 복사", "url": f"https://t.me/share/url?url={scenario}&text=쇼츠대본"}])
        
    if keyboard:
        payload["reply_markup"] = json.dumps({"inline_keyboard": keyboard})
        
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def analyze_and_script(art):
    """[핵심] 분석과 동시에 유튜브 쇼츠 대본까지 생성"""
    prompt = f"""당신은 한국 증시 전문가이자 100만 유튜버 시나리오 작가입니다.
글로벌 뉴스를 분석하여 '한국어' JSON으로 출력하세요.

[분석 가이드라인]:
1. title: 강렬한 한글 뉴스 제목.
2. impact: 한국 산업 및 관련 기업 수익성 분석.
3. stocks: 관련 국내 상장사 명시 (삼성전자, SK하이닉스 등).
4. score: 0~10점 (투자 긴급도).
5. youtube_shorts: 7.0점 이상일 경우, 60초 분량의 쇼츠 대본 작성.
   - [오프닝]: 시청자의 시선을 끄는 강력한 훅(Hook).
   - [본론]: 뉴스의 핵심 내용과 한국 증시 영향.
   - [결론]: 관련주 언급 및 투자 포인트.
   - [CTA]: 구독과 좋아요 유도.

뉴스 원문: {art['title']}
JSON 형식으로만 답변하세요."""

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.3-70b-versatile", 
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=data, timeout=30)
        return json.loads(res.json()['choices'][0]['message']['content'])
    except: return None

def main():
    send_to_boss("🚀 **크리에이터 엔진(v1.5.0) 가동**\n분석 리포트와 유튜브 대본을 동시에 생성합니다.")
    
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        report_count = 0
        for art in articles[:12]:
            res = analyze_and_script(art)
            if not res: continue
            
            score = float(res.get('score', 0))
            if score > 2.5: # 보고 기준 점수
                report = (f"📍 **뉴스**: {res.get('title')}\n"
                          f"🔥 **분석 ({score}점)**: {res.get('impact')}\n"
                          f"✅ **관련주**: {res.get('stocks')}\n"
                          f"📝 **요약**: {res.get('summary', '핵심 요약 참고')}")
                
                # 시나리오가 생성되었을 경우 별도 텍스트 준비
                scenario_text = res.get('youtube_shorts', None)
                send_to_boss(report, art['link'], scenario_text)
                
                # 시나리오가 있다면 보스에게 가독성 있게 한 번 더 전송
                if scenario_text and score >= 7.0:
                    time.sleep(2)
                    send_to_boss(f"🎬 **[유튜브 쇼츠 대본 - {res.get('title')}]**\n\n{scenario_text}")
                
                report_count += 1
                time.sleep(1)

        send_to_boss(f"✅ **생성 완료**\n- 총 {report_count}건의 전략 리포트 및 대본 송출 완료.")

    except Exception as e:
        send_to_boss(f"❌ **시스템 오류**: {str(e)}")

if __name__ == "__main__": main()
