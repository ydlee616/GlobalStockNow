import json, time, requests, os, re, torch
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")
INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

def send_telegram_msg(msg):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)

# Qwen Rescue Engine 로드
print("📂 Loading Qwen Rescue...")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct", torch_dtype="auto", device_map="cpu")

def call_ai(article):
    # 1단계: Gemini Pro 시도
    prompt = f"Analyze this news for Korean stock market impact. Output ONLY KOREAN JSON: {{\"title\": \"한글제목\", \"reason\": \"영향사유\", \"summary\": \"한글요약\", \"score\": 0.0-10.0}}\nNews: {article.get('title')}"
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}, timeout=30)
        if res.status_code == 200:
            text = res.json()['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(re.sub(r'```json|```', '', text).strip())
            return {**data, "engine": "Gemini_Pro", "source": article.get('source')}
    except: pass

    # 2단계: 실패 시 Qwen Rescue 투입
    print(f"   ⚔️ Qwen Rescue 투입: {article.get('title')[:15]}...")
    inputs = tokenizer(f"<|im_start|>system\n금융 분석가로서 한글로 JSON 출력하세요.<|im_end|>\n<|im_start|>user\nTitle: {article.get('title')}<|im_end|>\n<|im_start|>assistant\n", return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=256)
    try:
        text = tokenizer.decode(outputs[0], skip_special_tokens=True).split("assistant")[-1]
        data = json.loads(re.search(r'\{.*\}', text, re.DOTALL).group())
        return {**data, "engine": "Qwen_Rescue", "source": article.get('source')}
    except: return None

def analyze():
    if not os.path.exists(INPUT_FILE): return
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])[:15]

    if not articles:
        send_telegram_msg(f"📭 [#{RUN_NUMBER}] 분석할 데이터가 없습니다.")
        return

    results = []
    for art in articles:
        res = call_ai(art)
        if res: results.append(res)
        time.sleep(35)

    # 텔레그램 리포트 (보스 요청 4단계 양식)
    msg = f"🚀 **[GlobalStockNow #{RUN_NUMBER}] 분석 리포트**\n"
    for item in sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:5]:
        icon = "💎" if item.get('engine') == 'Gemini_Pro' else "⚔️"
        msg += f"\n{icon} **1. 제목: {item.get('title')}**\n"
        msg += f"   **2. 매체**: {item.get('source')}\n"
        msg += f"   **3. 영향도 ({item.get('score')}점)**: {item.get('reason')}\n"
        msg += f"   **4. 요약**: {item.get('summary')}\n"
        msg += "----------------------------\n"
    
    send_telegram_msg(msg)

if __name__ == "__main__":
    analyze()
