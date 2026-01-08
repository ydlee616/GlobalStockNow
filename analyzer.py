import json
import time
import requests
import os
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from datetime import datetime

# ==========================================
# [설정 영역]
# ==========================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")

# 영향도 기준 (무조건 나오게 2.0으로 낮춤)
IMPACT_THRESHOLD = 2.0

INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

# Gemini 설정
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # 🔥 [핵심 1] JSON 강제 모드
    generation_config = {
        "temperature": 1,
        "response_mime_type": "application/json",
    }
    
    # 🔥 [핵심 2] 안전장치 해제 (뉴스 분석 시 차단 방지)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    
    model = genai.GenerativeModel(
        'gemini-1.5-flash', 
        generation_config=generation_config,
        safety_settings=safety_settings
    )
else:
    print("❌ Error: GOOGLE_API_KEY가 없습니다.")

# ==========================================
# 1. 뉴스 분석 함수
# ==========================================
def analyze_news_batch(articles):
    results = []
    batch_size = 5
    
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작... (기준: {IMPACT_THRESHOLD}점)")

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        prompt = f"""
        You are a financial analyst. Analyze these news articles.
        MUST output a JSON list.
        
        [Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Fields Required]:
        - title (Korean summary title)
        - summary (Korean 1 sentence)
        - score (Float 0.0-10.0 impact score)
        - related_stocks (List of strings)
        """

        try:
            response = model.generate_content(prompt)
            
            # JSON 파싱
            batch_result = json.loads(response.text)
            
            if isinstance(batch_result, list):
                results.extend(batch_result)
            elif isinstance(batch_result, dict):
                if 'articles' in batch_result:
                    results.extend(batch_result['articles'])
                else:
                    results.append(batch_result)
            
            time.sleep(1)
            
        except Exception as e:
            print(f"⚠️ Error in batch {i}: {e}")
            # 에러 발생 시 텔레그램으로 로그 전송 (디버깅용)
            send_error_log(f"Batch {i} Error: {str(e)}")
            continue

    return results

# ==========================================
# 2. 에러 로그 전송 (텔레그램)
# ==========================================
def send_error_log(error_msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
        data={"chat_id": TELEGRAM_CHAT_ID, "text": f"⚠️ [Error #{RUN_NUMBER}] {error_msg}"}
    )

# ==========================================
# 3. 결과 저장 및 전송
# ==========================================
def save_and_notify(data):
    # 파일 저장
    output_data = {
        "analyzed_at": str(datetime.now()),
        "run_number": RUN_NUMBER,
        "count": len(data),
        "reports": data
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 분석 완료! 총 {len(data)}건 저장됨.")

    # 텔레그램 전송
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return

    # 점수 필터링
    important_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    important_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = important_news[:5]

    # 분석 결과가 0건이면 에러 메시지 전송
    if len(data) == 0:
        msg = f"🚫 **[GlobalStockNow #{RUN_NUMBER}] 분석 실패**\n\n"
        msg += "AI가 데이터를 반환하지 않았습니다. 로그를 확인하세요."
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        return

    # 중요 뉴스가 없을 때
    if not top_news:
        msg = f"📉 **[GlobalStockNow #{RUN_NUMBER}]**\n특이사항 없음 (모든 뉴스 {IMPACT_THRESHOLD}점 미만)"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        return

    # 정상 전송
    msg = f"🚀 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n(기준: {IMPACT_THRESHOLD}점 이상)\n\n"
    for item in top_news:
        score = item.get('score', 0)
        icon = "🔥" if score >= 7.0 else "⚡"
        msg += f"{icon} **{item.get('title')}** ({score}점)\n"
        msg += f"└ {item.get('summary')}\n"
        msg += f"└ 관련주: {', '.join(item.get('related_stocks', []))}\n\n"
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

# ==========================================
# 메인 실행부
# ==========================================
if __name__ == "__main__":
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            articles = raw_data.get('articles', [])
            
        if articles:
            results = analyze_news_batch(articles)
            save_and_notify(results)
        else:
            print("📭 뉴스 데이터 없음")
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
