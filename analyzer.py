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

# 영향도 기준 (2.0점 이상이면 전송)
IMPACT_THRESHOLD = 2.0
INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

# ==========================================
# 0. 텔레그램 전송 헬퍼
# ==========================================
def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=5)
    except: pass

# ==========================================
# 1. Gemini API 호출 (Flash 강제 고정)
# ==========================================
def call_gemini_flash(prompt):
    if not GOOGLE_API_KEY: return None

    # 🔥 [핵심] Pro 모델 절대 금지. Flash 모델 강제 지정.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    
    # JSON 포맷 강제 프롬프트
    full_prompt = prompt + "\n\nIMPORTANT: Output ONLY valid JSON array. No markdown code blocks."
    
    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.5, # 분석 정확도를 위해 온도 낮춤
            "responseMimeType": "application/json"
        }
    }

    # 재시도 로직 (Max 3회)
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            
            elif response.status_code == 429:
                print(f"⏳ 429 Quota Limit. 10초 대기 후 재시도... ({attempt+1}/3)")
                time.sleep(10)
                continue
            
            else:
                print(f"❌ API Error {response.status_code}: {response.text[:100]}")
                return None

        except Exception as e:
            print(f"❌ Connection Error: {e}")
            time.sleep(5)
            continue
            
    return None

# ==========================================
# 2. 뉴스 분석 (배치 처리)
# ==========================================
def analyze_news_batch(articles):
    results = []
    batch_size = 5 # Flash 모델은 5개씩 처리해도 충분함
    
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작 (Target: {len(articles)} articles)...")

    # 최대 25개까지만 분석 (안전하게 끊기)
    target_articles = articles[:25]

    for i in range(0, len(target_articles), batch_size):
        batch = target_articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        prompt = f"""
        You are a professional stock market analyst. 
        Analyze the following news articles and evaluate their impact on the stock market.
        
        [Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Requirements]:
        Return a JSON LIST of objects with these keys:
        - title: concise title in Korean.
        - summary: 1-sentence summary in Korean.
        - score: Float number (0.0 - 10.0) based on market impact.
        - related_stocks: List of related stock ticker symbols or names (e.g., ["Samsung", "SK Hynix"]).
        """

        response_text = call_gemini_flash(prompt)
        
        if response_text:
            try:
                # 가끔 마크다운 코드블록(```json)이 섞여 나올 때 제거
                clean_text = re.sub(r'```json\s*|\s*```', '', response_text)
                data = json.loads(clean_text)
                
                if isinstance(data, list): results.extend(data)
                elif isinstance(data, dict): 
                    if 'articles' in data: results.extend(data['articles'])
                    else: results.append(data)
            except Exception as e:
                print(f"⚠️ JSON Parsing Failed: {e}")
        
        # 🔥 Flash 모델 권장 속도 준수 (3초 휴식)
        time.sleep(3)

    return results

# ==========================================
# 3. 저장 및 전송
# ==========================================
def save_and_notify(data):
    # 결과 파일 저장
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
        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석 실패: 결과 데이터 없음")
        return

    # 중요 뉴스 필터링 (점수순 정렬)
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
            articles = raw_data.get('articles', [])
            
        if articles:
            results = analyze_news_batch(articles)
            save_and_notify(results)
        else:
            print("📭 뉴스 데이터 없음")
            # 데이터가 없을 때도 알림
            send_telegram_msg(f"📭 [GlobalStockNow #{RUN_NUMBER}] 수집된 뉴스가 없습니다.")
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
