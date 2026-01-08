import json
import time
import requests
import os
import re
import google.generativeai as genai
from datetime import datetime

# ==========================================
# [설정 영역]
# ==========================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")

# 🔥 핵심 변경: 영향도 기준을 3.0으로 설정 (기존 7.0 -> 3.0)
IMPACT_THRESHOLD = 3.0

INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("❌ Error: GOOGLE_API_KEY가 없습니다.")

# ==========================================
# 1. 뉴스 분석 함수
# ==========================================
def analyze_news_batch(articles):
    results = []
    batch_size = 5
    
    print(f"🔄 [Run #{RUN_NUMBER}] 분석 시작... (기준 점수: {IMPACT_THRESHOLD}점)")

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        # 프롬프트에 'score' 필드를 추가하고 0~10점 부여를 명시
        prompt = f"""
        You are a professional stock market analyst.
        Analyze the following news articles.
        
        [Input Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Requirement]:
        Return the result ONLY in valid JSON format (list of objects).
        Each object must have:
        - "title": A concise 1-line headline in Korean.
        - "summary": A 2-sentence summary in Korean.
        - "score": A float number between 0.0 and 10.0 indicating market impact (10 is huge impact).
        - "reason": Why you gave this score.
        - "related_stocks": List of related stock tickers.
        """

        try:
            response = model.generate_content(prompt)
            
            # 정규표현식으로 JSON 리스트([ ... ])만 추출
            match = re.search(r'\[.*\]', response.text, re.DOTALL)
            
            if match:
                clean_text = match.group()
                batch_result = json.loads(clean_text)
                
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                else:
                    results.append(batch_result)
            else:
                print(f"⚠️ Batch {i}: JSON 파싱 실패")

            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error in batch {i}: {e}")
            continue

    return results

# ==========================================
# 2. 결과 저장 함수
# ==========================================
def save_results(data):
    # 여기서 1차로 필터링하지 않고, 원본은 다 저장합니다.
    output_data = {
        "analyzed_at": str(datetime.now()),
        "run_number": RUN_NUMBER,
        "count": len(data),
        "reports": data
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 분석 완료! 총 {len(data)}건 저장됨.")
    return output_data

# ==========================================
# 3. 텔레그램 전송 함수 (필터링 적용)
# ==========================================
def send_telegram_report(analyzed_data):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    reports = analyzed_data.get('reports', [])
    
    # 🔥 여기서 점수(3.0) 이상인 것만 골라냅니다.
    important_news = [
        r for r in reports 
        if float(r.get('score', 0)) >= IMPACT_THRESHOLD
    ]
    
    # 점수 높은 순으로 정렬
    important_news.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # 상위 5개만 전송
    top_news = important_news[:5]

    if not top_news:
        message = f"📢 **[GlobalStockNow #{RUN_NUMBER}]**\n\n특이사항 없음 (모든 뉴스 영향도 {IMPACT_THRESHOLD} 미만)"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": message})
        return

    print(f"🚀 중요 뉴스 {len(top_news)}건 전송 시작...")
    
    message = f"📢 **[GlobalStockNow 속보 (#{RUN_NUMBER})]**\n"
    message += f"기준: 영향도 {IMPACT_THRESHOLD} 이상\n\n"
    
    for item in top_news:
        score = item.get('score', 0)
        # 이모지 결정
        icon = "🔥" if score >= 7.0 else "👀" if score >= 5.0 else "📢"
        
        message += f"{icon} **{item['title']}** (점수: {score})\n"
        message += f"└ {item['summary']}\n"
        message += f"└ 관련주: {', '.join(item.get('related_stocks', []))}\n\n"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    requests.post(url, data=payload)

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
            final_data = save_results(results)
            send_telegram_report(final_data)
        else:
            print("📭 뉴스 데이터 없음")
    else:
        print(f"❌ {INPUT_FILE} 파일 없음")
