import json
import time
import requests
import os
import google.generativeai as genai
from datetime import datetime

# ==========================================
# [설정 영역] GitHub Secrets & Env Variables
# ==========================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# GitHub Actions 실행 번호 가져오기 (없으면 'Local'로 표시)
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")

# 파일 경로
INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

# Gemini 설정
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("❌ Error: GOOGLE_API_KEY가 설정되지 않았습니다.")
    # 로컬 테스트가 아닐 경우 종료하고 싶다면 exit(1) 주석 해제
    # exit(1)

# ==========================================
# 1. 뉴스 분석 함수
# ==========================================
def analyze_news_batch(articles):
    results = []
    batch_size = 5
    
    print(f"🔄 [Run #{RUN_NUMBER}] 총 {len(articles)}개의 기사를 {batch_size}개씩 나누어 분석 시작...")

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        print(f"   Processing batch {i//batch_size + 1}...")
        
        prompt = f"""
        You are a professional stock market analyst.
        Analyze the following news articles and extract key insights for investors.
        
        [Input Articles]:
        {json.dumps(batch, ensure_ascii=False)}

        [Requirement]:
        Return the result ONLY in valid JSON format (list of objects).
        Do not use markdown code blocks.
        Each object must have:
        - "title": A concise 1-line headline in Korean.
        - "summary": A 2-sentence summary in Korean.
        - "impact": "Positive", "Negative", or "Neutral".
        - "related_stocks": List of related stock tickers or company names.
        """

        try:
            response = model.generate_content(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            batch_result = json.loads(clean_text)
            
            if isinstance(batch_result, list):
                results.extend(batch_result)
            else:
                results.append(batch_result)
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error in batch {i}: {e}")
            continue

    return results

# ==========================================
# 2. 결과 저장 함수
# ==========================================
def save_results(data):
    output_data = {
        "analyzed_at": str(datetime.now()),
        "run_number": RUN_NUMBER,  # 데이터 파일에도 번호 기록
        "count": len(data),
        "reports": data
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 분석 완료! {OUTPUT_FILE} 저장됨. (Run #{RUN_NUMBER}, 총 {len(data)}건)")
    return output_data

# ==========================================
# 3. 텔레그램 전송 함수 (제목 수정됨)
# ==========================================
def send_telegram_report(analyzed_data):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정이 없어 전송을 건너뜁니다.")
        return

    # 데이터가 없어도 '특이사항 없음' 메시지를 보내고 싶다면 아래 조건문을 수정해야 함
    # 현재는 데이터가 있을 때만 보냄
    if not analyzed_data['reports']:
        print("📭 전송할 분석 데이터가 없습니다.")
        return

    print("🚀 텔레그램 전송 시작...")
    
    top_reports = analyzed_data['reports'][:5] 
    
    # ▼▼▼ [수정된 부분] 제목에 파이프라인 번호 포함 ▼▼▼
    message = f"📢 **[GlobalStockNow 속보 브리핑 (#{RUN_NUMBER})]**\n"
    message += f"({analyzed_data['analyzed_at'][:16]})\n\n"
    
    for item in top_reports:
        icon = "🔥" if item.get('impact') == 'Positive' else "🔻" if item.get('impact') == 'Negative' else "➖"
        message += f"{icon} **{item['title']}**\n"
        message += f"└ {item['summary']}\n"
        message += f"└ 관련주: {', '.join(item.get('related_stocks', []))}\n\n"
    
    message += f"👉 총 {analyzed_data['count']}건 분석 완료."

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    try:
        requests.post(url, data=payload)
        print("✅ 텔레그램 메시지 전송 성공!")
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")

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
            print("📭 뉴스 데이터가 비어 있습니다.")
    else:
        print(f"❌ {INPUT_FILE} 파일을 찾을 수 없습니다.")
