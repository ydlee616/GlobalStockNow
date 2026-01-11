"""Module: analyzer.py | Version: 1.6.5 | Focus: Interactive Blog Generation"""
import json, time, requests, os, re

# 환경 변수 및 설정
BRAND_NAME = "GlobalStockNow 브리핑"
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_boss_with_buttons(msg, link, news_id):
    """보스의 컨펌을 받기 위한 5대 항목 리포트 전송"""
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # [지시사항] 5대 기본 항목 엄격 준수
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔗 뉴스 원문 보기", "url": link}],
            [{"text": "📝 블로그 초안 생성 (The Specialist)", "callback_data": f"draft_{news_id}"}]
        ]
    }
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(keyboard)
    }
    requests.post(url, data=payload, timeout=10)

def generate_the_specialist_blog(art_title):
    """[핵심] 보스가 승인한 7단계 블로그 생성 로직"""
    prompt = f"""당신은 'The Specialist' 블로그 작가입니다. 
다음 뉴스를 바탕으로 네이버/티스토리 검색 상위 노출을 위한 전문 포스팅을 작성하세요.
문체는 '슈카월드' 스타일의 위트와 속도감을 유지하십시오.

[반드시 포함할 7단계 구조]:
1. 뉴스 요약: 핵심 내용 3줄 요약.
2. 뉴스의 배경: 사건이 터진 거시적/산업적 배경.
3. 행간 읽기 & 비하인드: 기사 너머의 진짜 의도와 비화.
4. 역사적 앵커링: 과거 유사 사례와 주가 변동 패턴 대조.
5. 다차원 영향평가: 종목, 테마주, 관련주, 특징주별 정밀 평가.
6. 시가 추이 분석: 현재 종목들의 시가 추이와 비교 분석.
7. 문제 및 리스크: 향후 발생 가능한 변수와 주의사항.

뉴스 제목: {art_title}
결과는 마크다운(Markdown) 형식으로 출력하세요."""

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6
        }
        res = requests.post(url, headers=headers, json=data, timeout=30)
        return res.json()['choices'][0]['message']['content']
    except: return "블로그 초안 생성 중 오류가 발생했습니다."

def main():
    # 1. 뉴스 수집 데이터 로드
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        for i, art in enumerate(articles[:10]):
            # 2. 텔레그램 5대 항목 보고 (수동 컨펌용)
            # 여기서는 예시로 AI 분석을 거쳐 5개 항목을 만듭니다.
            report_msg = (f"🌍 **{BRAND_NAME} (#{RUN_NUMBER})**\n\n"
                          f"1️⃣ **뉴스 제목**: {art['title']}\n"
                          f"2️⃣ **출처**: Global News Source\n"
                          f"3️⃣ **주가 영향도**: 분석 대기 중...\n"
                          f"4️⃣ **관련주/테마**: 탐색 대기 중...\n"
                          f"5️⃣ **뉴스 요약**: {art.get('summary', '내용 없음')[:100]}...")
            
            send_to_boss_with_buttons(report_msg, art['link'], i)
            time.sleep(1)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__": main()
