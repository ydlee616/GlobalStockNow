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
# 1. Rescue Engine (Qwen) - 4단계 양식 학습
# ==========================================
print("📂 로컬 수색대(Qwen2.5-0.5B) 상시 대기 중...")
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype="auto", device_map="cpu")

def call_qwen_rescue(article):
    prompt = f"""<|im_start|>system
금융 분석가로서 뉴스를 분석하세요. 반드시 한글로 출력하세요.
JSON format: {{"title": "한글제목", "reason": "영향도 사유", "summary": "한글요약", "score": 0.0-10.0}}<|im_end|>
<|im_start|>user
Title: {article.get('title')}
Summary: {article.get('summary')}<|im_end|>
<|im_start|>assistant
"""
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=300, temperature=0.1)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    try:
        json_str = response.split("assistant")[-1].strip()
        data = json.loads(re.search(r'\{.*\}', json_str, re.DOTALL).group())
        return {**data, "source": article.get('source'), "engine": "Qwen_Rescue"}
    except: return None

# ==========================================
# 2. Main Engine (Gemini Pro) - 4단계 양식 학습
# ==========================================
def call_gemini_smart(article):
    if not GOOGLE_API_KEY: return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
    
    prompt = f"""
    Analyze this news for stock market impact. Output MUST be in KOREAN.
    News: {article.get('title')} - {article.get('summary')}
    
    Return ONLY JSON with these exact keys:
    {{
        "title": "한글 요약 제목",
        "reason": "한국 주식시장에 미치는 구체적 영향 사유",
        "summary": "뉴스 내용 핵심 요약",
        "score": 0.0-10.0
    }}
    """
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}],
        "generationConfig": {"temperature": 0.2}
    }

    try:
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            text = response.json()['candidates'][0]['content']['parts'][0]['text']
            result = json.loads(re.sub(r'```json|```', '', text).strip())
            result['source'] = article.get('source')
            result['engine'] = 'Gemini_Pro'
            return result
    except: pass
    return None

# ==========================================
# 3. 자율 실행 및 리포트 생성
# ==========================================
def orchestrate():
    if not os.path.exists(INPUT_FILE): return
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    final_results = []
    target_articles = articles[:15] # 우선 고품질 15건 분석

    for i, art in enumerate(target_articles):
        res = call_gemini_smart(art)
        if not res:
            res = call_qwen_rescue(art)
        
        if res:
            final_results.append(res)
        time.sleep(35)

    # 텔레그램 메시지 구성 (보스 요청 1, 2, 3, 4 순서)
    msg = f"🚀 **[GlobalStockNow #{RUN_NUMBER}] Ver 0.1 리포트**\n"
    for item in sorted(final_results, key=lambda x: x.get('score', 0), reverse=True)[:5]:
        engine_icon = "💎" if item.get('engine') == 'Gemini_Pro' else "⚔️"
        msg += f"\n{engine_icon} **1. 제목: {item.get('title')}**\n"
        msg += f"   **2. 매체**: {item.get('source')}\n"
        msg += f"   **3. 영향도 ({item.get('score')}점)**: {item.get('reason')}\n"
        msg += f"   **4. 요약**: {item.get('summary')}\n"
        msg += "----------------------------\n"
    
    send_telegram_msg(msg)

if __name__ == "__main__":
    orchestrate()
