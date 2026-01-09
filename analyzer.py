import json
import time
import requests
import os
import sys
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

IMPACT_THRESHOLD = 2.0
INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

# ==========================================
# 0. 모델 초기화 (하이브리드 방식)
# ==========================================
def init_model():
    if not GOOGLE_API_KEY:
        error_msg = "❌ FATAL: GOOGLE_API_KEY가 없습니다. Secrets를 확인하세요."
        print(error_msg)
        send_telegram_alert(error_msg)
        sys.exit(1)

    genai.configure(api_key=GOOGLE_API_KEY)
    
    generation_config = {
        "temperature": 1,
        "response_mime_type": "application/json",
    }
    
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    
    # 🔥 [수정됨] 모델 이름을 구체적으로 변경 (순차 시도)
    model_names = ['gemini-1.5-flash-latest', 'gemini-1.5-flash', 'gemini-1.5-flash-001', 'gemini-pro']
    
    for name in model_names:
        try:
            print(f"Testing model: {name}...")
            model = genai.GenerativeModel(
                name, 
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            # 테스트 호출 (연결 확인)
            model.generate_content("test") 
            print(f"✅ Model selected: {name}")
            return model
        except Exception as e:
            print(f"⚠️ {name} failed: {e}")
            continue
            
    # 모든 모델 실패 시
    send_telegram_alert("❌ 모든 AI 모델 연결 실패. API Key 권한을 확인하세요.")
    sys.exit(1)

def send_telegram_alert(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
            data={"chat_id": TELEGRAM_CHAT_ID, "text": f"⚠️ [System Alert #{RUN_NUMBER}] {msg}"}
        )

# 전역 모델 생성
model = init_model()

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
            print(f"⚠️ Batch {i} Error: {e}")
            # send_telegram_alert(f"Batch {i} Error: {str(e)}") # 너무 시끄러우면 주석 처리
            continue

    return results

# ==========================================
# 2. 결과 저장 및 전송
# ==========================================
def save_and_notify(data):
    output_data = {
        "analyzed_at": str(datetime.now()),
        "run_number": RUN_NUMBER,
        "count": len(data),
        "reports": data
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 분석 완료! 총 {len(data)}건 저장됨.")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return

    important_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    important_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = important_news[:5]

    if len(data) == 0:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                      data={"chat_id": TELEGRAM_CHAT_ID, "text": f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석 데이터 없음 (0건)", "parse_mode": "Markdown"})
        return

    msg = f"🚀 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n(기준: {IMPACT_THRESHOLD}점 이상)\n\n"
    
    if not top_news:
        msg += "특이사항 없음 (중요 뉴스 없음)"
    else:
        for item in top_news:
            score = item.get('score', 0)
            icon = "🔥" if score >= 7.0 else "⚡"
            msg += f"{icon} **{item.get('title')}** ({score}점)\n"
            msg += f"└ {item.get('summary')}\n"
            msg += f"└ 관련주: {', '.join(item.get('related_stocks', []))}\n\n"
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

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
