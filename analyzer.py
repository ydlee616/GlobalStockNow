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

IMPACT_THRESHOLD = 2.0
INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=5)
    except: pass

# ==========================================
# 1. Gemini API 호출 (안전장치 해제 + Flash)
# ==========================================
def call_gemini_flash(prompt):
    if not GOOGLE_API_KEY: return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    full_prompt = prompt + "\n\nIMPORTANT: Output ONLY valid JSON array. No markdown."
    
    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        # 🔥 [핵심] 안전 장치 완전 해제 (뉴스 분석 거부 방지)
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {
            "temperature": 0.5,
            "responseMimeType": "application/json"
        }
    }

    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                print(f"⏳ Quota Limit. Waiting 10s... ({attempt+1}/3)")
                time.sleep(10)
                continue
            else:
                # 에러 로그를 명확히 출력
                print(f"❌ API Error {response.status_code}: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            time.sleep(5)
            continue
            
    return None

# ==========================================
# 2. 뉴스 분석
# ==========================================
def analyze_news_batch(articles):
    results = []
    batch_size = 5 
    
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작 (News Count: {len(articles)})...")

    # 수집된 뉴스 전체 분석 (최대 35개)
    target_articles = articles[:35]

    for i in range(0, len(target_articles), batch_size):
        batch = target_articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        prompt = f"""
        You are a financial analyst. Analyze these news articles.
        
        [Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Requirements]:
        Return a JSON LIST of objects:
        - title (Korean)
        - summary (Korean)
        - score (Float 0-10)
        - related_stocks (List)
        """

        response_text = call_gemini_flash(prompt)
        
        if response_text:
            try:
                clean_text = re.sub(r'```json\s*|\s*```', '', response_text)
                data = json.loads(clean_text)
                if isinstance(data, list): results.extend(data)
                elif isinstance(data, dict): 
                    if 'articles' in data: results.extend(data['articles'])
                    else: results.append(data)
            except: 
                print("⚠️ JSON Parsing Failed")
        else:
            print(f"⚠️ Batch {i//batch_size + 1} Failed (Empty Response)")

        time.sleep(3)

    return results

# ==========================================
# 3. 저장 및 전송
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

    if not TELEGRAM_BOT_TOKEN: return

    if not data:
        # 분석 실패 시 에러 메시지 전송
        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석 실패: 안전 필터 또는 API 오류")
        return

    important_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    important_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = important_news[:5]

    msg = f"🚀 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n(모델: Gemini 1.5 Flash)\n\n"
    
    if not top_news:
        msg += "특이사항 없음 (중요 뉴스 없음)"
    else:
        for item in top_news:
            score = item.get('score', 0)
            icon = "🔥" if score >= 7.0 else "⚡"
            msg += f"{icon} **{item.get('title')}** ({score}점)\n"
            msg += f"└ {item.get('summary')}\n"
            msg += f"└ 관련주: {', '.join(item.get('related_stocks', []))}\n\n"
    
    send_telegram_msg(msg)

if __name__ == "__main__":
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            # 파일 형식이 리스트인지 딕셔너리인지 확인
            if isinstance(raw_data, list):
                articles = raw_data
            else:
                articles = raw_data.get('articles', [])
            
        if articles:
            results = analyze_news_batch(articles)
            save_and_notify(results)
        else:
            print("📭 뉴스 데이터 없음")
            send_telegram_msg(f"📭 [GlobalStockNow #{RUN_NUMBER}] 수집된 뉴스가 없습니다.")
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
