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
# 1. Gemini API 호출 (충돌 방지 로직 적용)
# ==========================================
def call_gemini_hybrid(prompt):
    if not GOOGLE_API_KEY: return None

    # 안정성이 가장 높은 Flash 모델 사용
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # [핵심 변경 1] API 레벨의 JSON 강제 모드(responseMimeType)를 끕니다. (충돌 원인 제거)
    # 대신 프롬프트로 강력하게 형식을 요구합니다.
    full_prompt = prompt + "\n\n[SYSTEM]: Output strictly a valid JSON list. Do not use Markdown block. Just plain text."

    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        # [핵심 변경 2] 안전 장치는 확실하게 끕니다. (뉴스 필터링 방지)
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {
            "temperature": 0.4 # 분석 일관성 유지
        }
    }

    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                try:
                    text = response.json()['candidates'][0]['content']['parts'][0]['text']
                    # [핵심 변경 3] 마크다운(```json)이나 불필요한 공백을 파이썬이 직접 청소
                    clean_text = re.sub(r'```json|```', '', text).strip()
                    # 유효성 검사: JSON 로드 시도
                    json.loads(clean_text)
                    return clean_text
                except (KeyError, IndexError, json.JSONDecodeError):
                    # 가끔 AI가 이상한 말을 섞으면 재시도
                    print(f"⚠️ Response parsing failed. Retrying... ({attempt+1})")
                    time.sleep(2)
                    continue
            
            elif response.status_code == 429:
                print(f"⏳ Quota Limit. 10s Cooling... ({attempt+1})")
                time.sleep(10)
                continue
            else:
                print(f"❌ API Error {response.status_code}: {response.text[:200]}")
                # 치명적 오류(400/500)는 즉시 보고
                if attempt == 0:
                    send_telegram_msg(f"⚠️ [Debug #{RUN_NUMBER}] 구글 API 에러: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            time.sleep(5)
            continue
            
    return None

# ==========================================
# 2. 뉴스 분석 로직
# ==========================================
def analyze_news_batch(articles):
    results = []
    batch_size = 5 
    
    # 전체 뉴스 중 최대 30개만 처리 (Quota 보호)
    target_articles = articles[:30]
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작 (대상: {len(target_articles)}건)...")

    for i in range(0, len(target_articles), batch_size):
        batch = target_articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        prompt = f"""
        You are a financial analyst. Analyze these news items.
        
        [Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Requirement]:
        Return a JSON LIST of objects with:
        - title (Korean summary)
        - summary (Korean, 1 sentence)
        - score (Float 0.0-10.0 impact)
        - related_stocks (List of strings)
        """

        response_text = call_gemini_hybrid(prompt)
        
        if response_text:
            try:
                data = json.loads(response_text)
                if isinstance(data, list): results.extend(data)
                elif isinstance(data, dict): 
                    if 'articles' in data: results.extend(data['articles'])
                    else: results.append(data)
            except: 
                print("⚠️ Batch skipped (Invalid JSON)")
        
        # 5초 휴식 (안전 운전)
        time.sleep(5)

    return results

# ==========================================
# 3. 저장 및 알림
# ==========================================
def save_and_notify(data):
    # 결과 저장
    output_data = {"analyzed_at": str(datetime.now()), "run_number": RUN_NUMBER, "reports": data}
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 분석 완료! 총 {len(data)}건 저장됨.")

    if not TELEGRAM_BOT_TOKEN: return

    # 분석된 결과가 없으면 알림
    if not data:
        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석 결과 없음 (API 응답 실패)")
        return

    # 중요 뉴스 필터링
    top_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    top_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = top_news[:5]

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
            if isinstance(raw_data, list): articles = raw_data
            else: articles = raw_data.get('articles', [])
            
        if articles:
            results = analyze_news_batch(articles)
            save_and_notify(results)
        else:
            print("📭 뉴스 데이터 없음")
            # [중요] 수집된 뉴스가 없으면 텔레그램으로 알려줌 (사용자 안심용)
            send_telegram_msg(f"📭 [GlobalStockNow #{RUN_NUMBER}] 현재 수집된 새 뉴스가 없습니다.\n(Collector가 빈손으로 돌아왔습니다)")
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
        send_telegram_msg(f"❌ [GlobalStockNow #{RUN_NUMBER}] 데이터 파일 없음")
