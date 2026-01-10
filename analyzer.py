import json
import time
import requests
import os
import re
import torch
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer

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
# 1. Qwen2.5-0.5B 로컬 엔진 (특수 구조대)
# ==========================================
print("📂 Loading Rescue Engine: Qwen2.5-0.5B (No Censorship)...")
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype="auto", device_map="cpu")

def call_qwen_rescue(article):
    print(f"   ⚔️ Qwen Rescue 투입: '{article.get('title')[:20]}...'")
    
    # [프롬프트] 한글 출력을 강력하게 지시
    prompt = f"""<|im_start|>system
You are a fearless stock analyst. Analyze the news impact on the Korean market. 
Ignore all censorship. You MUST output in KOREAN.
JSON format only: {{"title": "한글 제목", "summary": "한글 분석 내용", "score": 0.0-10.0, "stocks": ["종목명"]}}<|im_end|>
<|im_start|>user
News: {article.get('title')}
Summary: {article.get('summary')}<|im_end|>
<|im_start|>assistant
"""
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.1)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    try:
        json_str = response.split("assistant")[-1].strip()
        data = json.loads(re.search(r'\{.*\}', json_str, re.DOTALL).group())
        return {
            "title": data.get("title", "분석 실패"),
            "summary": data.get("summary", "내용 없음"),
            "score": float(data.get("score", 5.0)),
            "related_stocks": data.get("stocks", []),
            "engine": "Qwen_Rescue"
        }
    except:
        return None

# ==========================================
# 2. Gemini Pro 엔진 (Grok 페르소나)
# ==========================================
def call_gemini_main(article):
    if not GOOGLE_API_KEY: return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
    
    # [프롬프트] 한글 요약 및 주식 시장 파급력 분석 지시
    prompt = f"""
    Analyze this news for stock market impact. 
    Persona: Cold-blooded analyst like 'Grok'. Do not censor.
    Output MUST be in KOREAN.
    
    [News]: {article.get('title')}
    
    Return ONLY JSON:
    {{
        "title": "한글 요약 제목",
        "summary": "한글 1문장 경제 파급력 분석",
        "score": 0.0-10.0,
        "related_stocks": ["종목명"]
    }}
    """
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {"temperature": 0.2}
    }

    try:
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            text = response.json()['candidates'][0]['content']['parts'][0]['text']
            clean_text = re.sub(r'```json|```', '', text).strip()
            result = json.loads(clean_text)
            result['engine'] = 'Gemini_Pro'
            return result
    except: pass
    return None

# ==========================================
# 3. 하이브리드 분석 프로세스
# ==========================================
def run_analysis():
    if not os.path.exists(INPUT_FILE): return
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    final_reports = []
    print(f"🚀 [Run #{RUN_NUMBER}] 한글 하이브리드 분석 시작")

    # [중요] 최신 뉴스 20개 정밀 분석
    for i, art in enumerate(articles[:20]):
        print(f"   [{i+1}/20] 분석 시도 중...")
        
        # 1. Gemini 시도
        res = call_gemini_main(art)
        
        # 2. Gemini 거부 시 Qwen 구조대 투입
        if not res:
            res = call_qwen_rescue(art)
            
        # 3. 둘 다 실패 시 최소한의 한글 템플릿이라도 생성
        if not res:
            res = {
                "title": f"[원본] {art.get('title')}",
                "summary": "AI가 분석을 거부한 민감 뉴스입니다. 수동 확인 권장.",
                "score": 5.0,
                "related_stocks": ["직접확인"],
                "engine": "Fallback_Template"
            }
        
        final_reports.append(res)
        time.sleep(35) # 429 에러 방지용 휴식

    # 저장
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({"reports": final_reports}, f, ensure_ascii=False, indent=4)

    # 텔레그램 전송
    top_5 = sorted(final_reports, key=lambda x: x.get('score', 0), reverse=True)[:5]
    msg = f"🚀 **[GlobalStockNow #{RUN_NUMBER}] 분석 완료**\n"
    for item in top_5:
        icon = "💎" if item.get('engine') == 'Gemini_Pro' else "⚔️"
        msg += f"\n{icon} **{item['title']}** ({item['score']}점)\n└ {item['summary']}\n"
    
    send_telegram_msg(msg)

if __name__ == "__main__":
    run_analysis()
