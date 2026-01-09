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
        requests.post(url, data=payload, timeout=10)
    except: pass

# ==========================================
# 1. Gemini API 호출 (검열 해제 + Pro 모델)
# ==========================================
def call_gemini_pro_forced(prompt):
    if not GOOGLE_API_KEY: return None

    # [전략] 가장 안정적인 'gemini-pro' 모델 고정
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # [프롬프트] JSON 포맷 강제
    full_prompt = prompt + "\n\n[SYSTEM]: You must output a valid JSON list. Do not use Markdown. No explanation."

    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        # [핵심] 모든 안전 장치 'BLOCK_NONE'으로 해제 (전쟁/범죄 뉴스 분석 허용)
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {"temperature": 0.1} # 창의성 최소화 (포맷 준수)
    }

    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                res_json = response.json()
                
                # [예외처리] AI가 안전 문제로 답변을 거부했는지 확인
                if 'candidates' in res_json and not res_json['candidates'][0].get('content'):
                    finish_reason = res_json['candidates'][0].get('finishReason')
                    print(f"⚠️ Content Blocked (Reason: {finish_reason})")
                    return "[]" # 빈 리스트 문자열 반환 (에러 아님)

                text = res_json['candidates'][0]['content']['parts'][0]['text']
                # 마크다운 청소
                clean_text = re.sub(r'```json|```', '', text).strip()
                return clean_text
            
            elif response.status_code == 429:
                print(f"⏳ 429 API Limit. 40초 대기... ({attempt+1}/3)")
                time.sleep(40)
                continue
            
            else:
                print(f"❌ API Error {response.status_code}: {response.text[:200]}")
                time.sleep(5)
                continue

        except Exception as e:
            print(f"❌ Connection Error: {e}")
            time.sleep(10)
            continue
            
    return None

# ==========================================
# 2. 뉴스 분석 (배치 축소 + 긴 휴식)
# ==========================================
def analyze_news_batch(articles):
    results = []
    # [전략] 배치 사이즈를 3개로 줄여서 '위험한 뉴스'가 전체를 망치지 않게 함
    batch_size = 3
    
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작 (Total: {len(articles)})...")

    # 전체 뉴스 처리
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        prompt = f"""
        Analyze these news articles for stock market impact.
        
        [Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Requirements]:
        Return a JSON LIST of objects with keys:
        - title (Korean summary)
        - summary (Korean 1 sentence)
        - score (Float 0-10)
        - related_stocks (List of strings)
        """

        response_text = call_gemini_pro_forced(prompt)
        
        if response_text:
            try:
                # 응답이 비어있거나 [] 인 경우 처리
                if not response_text or response_text == "[]":
                    print("   ⚠️ Empty response (Skipped)")
                else:
                    data = json.loads(response_text)
                    if isinstance(data, list): results.extend(data)
                    elif isinstance(data, dict): 
                        if 'articles' in data: results.extend(data['articles'])
                        else: results.append(data)
            except: 
                print("⚠️ JSON Parsing Failed (Skipping batch)")
        
        # [전략] 40초 강제 휴식 (무조건 지켜야 함)
        print("   ☕ Cooling down 40s...")
        time.sleep(40)

    return results

# ==========================================
# 3. 결과 저장 및 전송
# ==========================================
def save_and_notify(data):
    output_data = {"analyzed_at": str(datetime.now()), "run_number": RUN_NUMBER, "reports": data}
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 분석 완료! 총 {len(data)}건 저장됨.")

    if not TELEGRAM_BOT_TOKEN: return

    if not data:
        # 데이터가 0건이면 로그 분석 요청
        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석 결과 0건.\n(원인: 모든 뉴스가 필터링되었거나 API 연결 실패)")
        return

    top_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    top_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = top_news[:5]

    msg = f"🚀 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n(분석 완료: {len(data)}건)\n\n"
    
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
            # 뉴스 없음은 정상이므로 알림 생략
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
