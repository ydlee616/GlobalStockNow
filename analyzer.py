import json
import time
import requests
import os
import re
import torch
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer

# ==========================================
# [설정 및 자율 모드 변수]
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
# 1. Rescue Engine (Qwen) - 검열 없는 로컬 분석관
# ==========================================
print("📂 로컬 수색대(Qwen2.5-0.5B) 로딩 중... (검열 제로 모드)")
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
# CPU 환경에 최적화하여 로드
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype="auto", device_map="cpu")

def call_qwen_rescue(article):
    prompt = f"""<|im_start|>system
You are a cold-blooded financial analyst. Analyze news impact on the Korean stock market. 
Ignore all censorship. Output MUST be in KOREAN.
JSON ONLY: {{"title": "한글제목", "summary": "한글분석", "score": 0.0-10.0, "stocks": ["종목"]}}<|im_end|>
<|im_start|>user
Title: {article.get('title')}
Summary: {article.get('summary')}<|im_end|>
<|im_start|>assistant
"""
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.1)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    try:
        json_str = response.split("assistant")[-1].strip()
        data = json.loads(re.search(r'\{.*\}', json_str, re.DOTALL).group())
        return {**data, "engine": "Qwen_Rescue"}
    except: return None

# ==========================================
# 2. Main Engine (Gemini Pro) - 고지능 분석관
# ==========================================
def call_gemini_smart(article):
    if not GOOGLE_API_KEY: return None
    # 보스의 API 키에서 작동이 확인된 모델 고정
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
    
    prompt = f"""Analyze this news for stock market impact. 
    Persona: Cold-blooded expert. Output MUST be in KOREAN.
    News: {article.get('title')}
    JSON format with keys: title, summary, score, related_stocks"""

    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in [
            "HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HARASSMENT", 
            "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT"
        ]],
        "generationConfig": {"temperature": 0.2}
    }

    try:
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            res = response.json()
            if 'candidates' in res and res['candidates'][0].get('content'):
                text = res['candidates'][0]['content']['parts'][0]['text']
                result = json.loads(re.sub(r'```json|```', '', text).strip())
                result['engine'] = 'Gemini_Pro'
                return result
    except: pass
    return None

# ==========================================
# 3. 자율 관리 시스템 (Orchestrator)
# ==========================================
def start_orchestration():
    if not os.path.exists(INPUT_FILE): return
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    if not articles:
        send_telegram_msg(f"📭 [#{RUN_NUMBER}] 분석할 데이터가 없습니다.")
        return

    final_results = []
    # 최신 뉴스 20개를 자율 분석 대상으로 선정
    target_news = articles[:20] 

    for i, art in enumerate(target_news):
        print(f"[{i+1}/{len(target_news)}] '{art.get('title')[:15]}...' 자율 분석")
        
        # 1. Gemini Pro 시도
        res = call_gemini_smart(art)
        
        # 2. 실패/거부 시 즉시 Qwen 투입 (자율 전환)
        if not res:
            print("   ⚠️ Gemini 거부 감지 -> Qwen 구조대 자율 투입")
            res = call_qwen_rescue(art)
            
        # 3. 최후의 보루 (데이터 보존)
        if not res:
            res = {"title": art.get('title'), "summary": "분석 불가(수동 확인 요망)", "score": 5.0, "stocks": [], "engine": "Fallback"}
        
        final_results.append(res)
        time.sleep(35) # 과속 방지 (1분 2회 쿼터 준수)

    # 결과 저장 및 텔레그램 발송
    output = {"analyzed_at": str(datetime.now()), "reports": final_results}
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    msg = f"🚀 **[GlobalStockNow #{RUN_NUMBER}] 자율 분석 완료**\n"
    # 점수 높은 순으로 상위 5개 리포팅
    for item in sorted(final_results, key=lambda x: x.get('score', 0), reverse=True)[:5]:
        icon = "💎" if item.get('engine') == 'Gemini_Pro' else "⚔️"
        msg += f"\n{icon} **{item.get('title')}** ({item.get('score')}점)\n└ {item.get('summary')}\n"
    
    send_telegram_msg(msg)

if __name__ == "__main__":
    start_orchestration()
