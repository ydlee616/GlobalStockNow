import json
import time
import requests
import os
import re
from datetime import datetime

# ==========================================
# [설정 영역]
# ==========================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")

INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=10)
    except: pass

# ==========================================
# 1. Gemini API 호출 (실패 시 원본 반환)
# ==========================================
def analyze_article_final(article):
    # 기본값 (AI 실패 시 사용할 원본 데이터)
    fallback_result = {
        "title": article.get('title', 'No Title'),
        "summary": f"[AI 분석 불가/원본] {article.get('summary', '')[:200]}...", # 원본 요약 사용
        "score": 5.0, # 중립 점수 부여
        "related_stocks": ["Manual_Check"],
        "ai_status": "failed"
    }

    if not GOOGLE_API_KEY: 
        return fallback_result

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # 프롬프트: JSON 포맷 강제
    prompt = f"""
    Analyze this news for stock market impact.
    [News Title]: {article.get('title')}
    [News Summary]: {article.get('summary')}
    
    OUTPUT JSON ONLY:
    {{
        "title": "Korean Title",
        "summary": "Korean Summary",
        "score": 0.0-10.0,
        "related_stocks": ["Stock1", "Stock2"]
    }}
    """

    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {"temperature": 0.1}
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            try:
                text = response.json()['candidates'][0]['content']['parts'][0]['text']
                clean_text = re.sub(r'```json|```', '', text).strip()
                result = json.loads(clean_text)
                result['ai_status'] = 'success'
                return result # 성공 시 AI 결과 반환
            except:
                print(f"⚠️ JSON 파싱 실패 -> 원본 사용: {article.get('title')[:10]}")
                return fallback_result # 파싱 실패 시 원본 반환
        
        elif response.status_code == 429:
            print("⏳ 429 Rate Limit. (Using Fallback)")
            time.sleep(30) # 429 발생 시 휴식 후 원본 반환
            return fallback_result
            
        else:
            print(f"❌ API Error {response.status_code}. (Using Fallback)")
            return fallback_result

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return fallback_result

# ==========================================
# 2. 전체 뉴스 처리 Loop
# ==========================================
def process_all_news(articles):
    results = []
    print(f"🔄 [Run #{RUN_NUMBER}] 처리 시작 (총 {len(articles)}건)...")
    
    # 전체 뉴스 처리
    for i, article in enumerate(articles):
        # 1. 분석 시도 (실패해도 원본이 나옴)
        res = analyze_article_final(article)
        results.append(res)
        
        status = res.get('ai_status', 'failed')
        print(f"   [{i+1}/{len(articles)}] {status.upper()}: {res.get('title')[:20]}...")
        
        # 2. API 쿨타임 준수 (성공 여부 상관없이 32초 휴식)
        # Gemini Free/Pro는 분당 요청 제한이 있으므로 필수
        time.sleep(32)

    return results

# ==========================================
# 3. 저장 및 알림
# ==========================================
def save_and_notify(data):
    # 결과 저장
    output_data = {
        "analyzed_at": str(datetime.now()),
        "run_number": RUN_NUMBER,
        "count": len(data),
        "reports": data
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 저장 완료: 총 {len(data)}건")

    if not TELEGRAM_BOT_TOKEN: return

    if not data:
        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 데이터 없음 (입력 파일 확인 필요)")
        return

    # 텔레그램 메시지 작성
    msg = f"🚀 **[GlobalStockNow 결과 (#{RUN_NUMBER})]**\n(총 {len(data)}건 처리됨)\n\n"
    
    # 상위 5개 전송 (점수순)
    # score가 없는 경우 0으로 처리하여 정렬
    top_news = sorted(data, key=lambda x: float(x.get('score', 0)), reverse=True)[:5]
    
    for item in top_news:
        title = item.get('title')
        summary = item.get('summary')
        score = item.get('score', 0)
        
        # AI 실패로 원본이 저장된 경우 표시
        icon = "🔥" if score >= 7 else "⚡"
        if item.get('ai_status') == 'failed':
            icon = "⚠️"
            title = f"[AI분석불가] {title}"
            
        msg += f"{icon} **{title}** ({score}점)\n"
        msg += f"└ {summary}\n\n"
        
    send_telegram_msg(msg)

if __name__ == "__main__":
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            # JSON 구조에 따라 리스트 추출
            if isinstance(raw_data, list): articles = raw_data
            elif isinstance(raw_data, dict): articles = raw_data.get('articles', [])
            else: articles = []
            
        if articles:
            # [테스트 모드] 시간 관계상 앞쪽 10개만 먼저 테스트 권장
            # 전체를 다 하려면: process_all_news(articles)
            results = process_all_news(articles[:10]) 
            save_and_notify(results)
        else:
            print("📭 뉴스 데이터 없음")
            # 입력 파일이 비어있으면 빈 리스트라도 저장
            save_and_notify([])
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
