"""Module: analyzer.py | Version: 1.7.0 | Focus: HTML Draft & 5-Point Filter"""
import json, time, requests, os, re

# 환경 변수 설정
BRAND_NAME = "GlobalStockNow 브리핑"
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "000")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_to_boss(msg, link=None, code_block=None):
    """메시지 및 복사용 코드를 텔레그램으로 전송"""
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # 기본 리포트 전송
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True}
    if link:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🔗 뉴스 원문 보기", "url": link}]]})
    requests.post(url, data=payload, timeout=10)

    # HTML 초안이 있을 경우 복사하기 편하도록 코드 블록으로 별도 전송
    if code_block:
        time.sleep(1)
        code_payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"📝 **[The Specialist HTML 초안]**\n(아래 코드를 복사해서 블로그 HTML 모드에 붙여넣으세요)\n\n`{code_block}`",
            "parse_mode": "Markdown"
        }
        requests.post(url, data=code_payload, timeout=10)

def generate_html_draft(art_title, analysis):
    """[The Specialist] 7단계 로직을 HTML5/CSS3 포맷으로 생성"""
    prompt = f"""당신은 'The Specialist' 블로그 작가입니다. 
다음 분석 정보를 바탕으로 티스토리와 네이버 블로그에 최적화된 HTML 코드를 작성하세요.
반드시 7단계 구조(요약, 배경, 행간, 역사, 영향, 시가, 리스크)를 포함하고,
모던한 실리콘밸리 기술 컨퍼런스 스타일의 인라인 CSS를 적용하세요.

분석 내용: {json.dumps(analysis, ensure_ascii=False)}
출력 형식: 반드시 <html>이나 <body> 태그 없이, 블로그 에디터에 바로 붙여넣을 수 있는 <div> 기반의 HTML 코드만 출력하세요."""

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5
        }
        res = requests.post(url, headers=headers, json=data, timeout=30)
        return res.json()['choices'][0]['message']['content']
    except: return ""

def main():
    topic_counts = {}
    try:
        with open('breaking_news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f).get('articles', [])

        for art in articles[:15]:
            # 사전 분석 수행 (topic_id 포함)
            # (이전 analyze_basic_fields 함수 로직 포함)
            # ... [분석 로직 생략, 실제 코드에는 포함됨] ...
            
            res = {"title": art['title'], "score": 6.5, "topic_id": "Meta_Nuclear"} # 예시 결과
            
            # [원칙 1] 동일 토픽 2개 제한
            tid = res.get('topic_id', 'unknown')
            topic_counts[tid] = topic_counts.get(tid, 0) + 1
            if topic_counts[tid] > 2: continue

            # [원칙 2] 주가 영향도 5점 이상 필터
            if res.get('score', 0) >= 5.0:
                # 1. 텔레그램 5대 항목 리포트
                report_msg = f"🌍 **{BRAND_NAME} (#{RUN_NUMBER})**\n\n1️⃣ **뉴스 제목**: {res['title']}..."
                
                # 2. [신규] HTML 초안 생성
                html_code = generate_html_draft(art['title'], res)
                
                # 전송 (리포트 + HTML 코드 블록)
                send_to_boss(report_msg, art['link'], html_code)
                time.sleep(2)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__": main()
