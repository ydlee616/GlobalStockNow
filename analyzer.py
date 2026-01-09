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
# 1. Gemini API 호출 (Pro 모델 + 안전장치 완전 해제)
# ==========================================
def call_gemini_pro_secure(prompt):
    if not GOOGLE_API_KEY: return None

    # 🔥 [전략 1] 404가 뜨는 Flash 대신, 작동이 확인된 'gemini-pro' 고정 사용
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # JSON 형식 강제 (프롬프트 레벨)
    full_prompt = prompt + "\n\n[SYSTEM]: Output strictly a valid JSON list. Do not use Markdown block. Just plain text."

    data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        # 🔥 [전략 2] "War", "Dead" 등 뉴스 키워드에 쫄지 않도록 안전장치 OFF
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {
            "temperature": 0.3 # 분석의 정확성을 위해 창의성 낮춤
        }
    }

    # 재시도 로직 (최대 3회)
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60) # 타임아웃 넉넉하게
            
            # 성공 (200 OK)
            if response.status_code == 200:
                try:
                    text = response.json()['candidates'][0]['content']['parts'][0]['text']
                    # 마크다운 코드블록(```json) 제거 청소
                    clean_text = re.sub(r'```json|```', '', text).strip()
                    # 유효한 JSON인지 미리 검사
                    json.loads(clean_text)
                    return clean_text
                except Exception as e:
                    print(f"⚠️ 데이터 파싱 오류 (재시도 중): {e}")
            
            # 429 과속 방지 (이미 40초를 쉬지만 혹시 몰라 추가 대기)
            elif response.status_code == 429:
                print(f"⏳ 429 과속 감지. 60초 대기 후 재시도... ({attempt+1}/3)")
                time.sleep(60)
                continue
            
            # 그 외 에러 로그 출력
            else:
                print(f"❌ API Error {response.status_code}: {response.text[:200]}")
                return None

        except Exception as e:
            print(f"❌ 통신 오류: {e}")
            time.sleep(10)
            continue
            
    return None

# ==========================================
# 2. 뉴스 분석 루프 (느림의 미학)
# ==========================================
def analyze_news_batch(articles):
    results = []
    # 한 번에 4개씩 묶어서 처리
    batch_size = 4
    
    # 현재 breaking_news.json에 34개가 있으므로 약 9번 반복 예정
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작 (Model: gemini-pro / Mode: Safety Compliant)...")

    # 최대 34개까지만 처리 (전체 다 처리함)
    target_articles = articles[:36]

    for i in range(0, len(target_articles), batch_size):
        batch = target_articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}/{len(target_articles)//batch_size + 1}...")
        
        prompt = f"""
        Analyze the following financial news articles.
        
        [Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Requirement]:
        Return a JSON LIST of objects with these exact keys:
        - title (Korean summary)
        - summary (Korean 1 sentence)
        - score (Float 0.0-10.0 impact score)
        - related_stocks (List of strings)
        """

        response_text = call_gemini_pro_secure(prompt)
        
        if response_text:
            try:
                data = json.loads(response_text)
                if isinstance(data, list): results.extend(data)
                elif isinstance(data, dict): 
                    if 'articles' in data: results.extend(data['articles'])
                    else: results.append(data)
            except: 
                print("⚠️ JSON 변환 실패 (배치 건너뜀)")
        else:
             print("⚠️ 응답 없음 (API 호출 실패)")
        
        # 🔥 [전략 3] 가장 중요: 40초 강제 휴식
        # 무료 등급은 1분에 2회 요청 제한이 있으므로, 1회 요청 후 40초를 쉬어야 안전합니다.
        # 답답하시겠지만 이 시간을 줄이면 429 에러가 다시 뜹니다.
        print("   ☕ API 제한 준수를 위해 40초 대기 중...")
        time.sleep(40)

    return results

# ==========================================
# 3. 저장 및 알림
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
        # 실패 시 텔레그램으로 명확히 알림
        send_telegram_msg(f"🚫 [GlobalStockNow #{RUN_NUMBER}] 분석 결과 없음. (로그 확인 필요)")
        return

    # 중요 뉴스 필터링 (점수순)
    top_news = [r for r in data if float(r.get('score', 0)) >= IMPACT_THRESHOLD]
    top_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_news = top_news[:5]

    msg = f"🚀 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n(안전모드 완료)\n\n"
    
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
            # JSON 호환성 처리
            if isinstance(raw_data, list): articles = raw_data
            else: articles = raw_data.get('articles', [])
            
        if articles:
            results = analyze_news_batch(articles)
            save_and_notify(results)
        else:
            print("📭 뉴스 데이터 없음")
            # 데이터 없음은 정상 상황일 수 있으므로 로그만 남김
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
