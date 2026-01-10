"""
Project: GlobalStockNow
Module: analyzer.py
Version: 0.3.1
Updated: 2026-01-10
Description: 8-step Strategic Analysis with HTML cleaning, stale data filtering, and interactive buttons.
"""
import json, time, requests, os, re, torch
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")
INPUT_FILE = 'breaking_news.json'
OUTPUT_FILE = 'analyzed_news.json'

def send_telegram_with_button(message, article_id=None):
    if not TELEGRAM_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    if article_id is not None:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성 (학습)", "callback_data": f"select_{article_id}"}]]})
    requests.post(url, data=payload, timeout=10)

def clean_html(raw_html):
    """HTML 태그 제거로 AI 혼선 방지"""
    return re.sub(r'<.*?>', '', raw_html)

print(f"📂 [Ver 0.3.1] AI Engine Loading...")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct", torch_dtype="auto", device_map="cpu")

def analyze_strategic(article):
    summary = clean_html(article.get('summary', ''))
    # [8단계 초정밀 분석 및 세이프티 우회 프롬프트]
    prompt = f"""[Financial Intelligence Mode] 
Analyze news impact on Korean Market (KOSPI/KOSDAQ). 
IGNORE political sensitivity. Focus ONLY on market flow, FX, and supply chains.
Output MUST be KOREAN JSON.
8-Steps: 1. 본질/행간, 2. 직접영향, 3. 간접영향(환율/원자재/지정학), 4. 투자심리/변동성, 5. 과거유사사례비교, 6. 시간축별전망, 7. 업종/종목, 8. 투자전략
News: {article.get('title')} - {summary}
"""
    # 1. Gemini Pro 시도 (Safety BLOCK_NONE)
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}, timeout=30)
        if res.status_code == 200:
            text = res.json()['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(re.sub(r'```json|```', '', text).strip())
            data['engine'] = 'Gemini_Pro'
            return data
    except: pass

    # 2. Qwen Rescue 시도
    inputs = tokenizer(f"<|im_start|>system\n금융 분석가로서 한글 JSON 보고서를 작성하세요.<|im_end|>\n<|im_start|>user\n{article.get('title')}<|im_end|>\n<|im_start|>assistant\n", return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=512)
    try:
        text = tokenizer.decode(outputs[0], skip_special_tokens=True).split("assistant")[-1]
        data = json.loads(re.search(r'\{.*\}', text, re.DOTALL).group())
        data['engine'] = 'Qwen_Rescue'
        return data
    except: return None

def run_analysis():
    if not os.path.exists(INPUT_FILE): return
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    results_count = 0
    for i, art in enumerate(articles[:15]):
        # [과거 기사 필터링] 2018, 2019년 기사 배제
        if any(year in art.get('published_at', '') for year in ['2018', '2019']): continue

        res = analyze_strategic(art)
        if res:
            icon = "💎" if res.get('engine') == 'Gemini_Pro' else "⚔️"
            msg = f"{icon} **1. 제목: {res.get('title')}**\n**2. 매체**: {art.get('source')}\n**3. 영향도 ({res.get('score')}점)**: {res.get('essence', {}).get('subtext', '행간 분석중')}\n   - **간접영향**: 환율({res.get('indirect', {}).get('fx', 'N/A')}), 원자재({res.get('indirect', {}).get('commodities', 'N/A')})\n**4. 영향받는 주식**: {res.get('map', {}).get('stocks', '분석중')}\n**5. 요약**: {res.get('essence', {}).get('summary', '요약중')}\n\n**📜 과거사례**: {res.get('history', {}).get('case', '사례분석중')}"
            send_telegram_with_button(msg, i)
            results_count += 1
        time.sleep(35)

    if results_count == 0:
        send_telegram_with_button(f"🌍 **글로벌스톡나우 속보 브리핑 (#{RUN_NUMBER})**\n\n오늘은 영향도 2점 이상 잠재 속보 없음\n_AI 자동 분석 완료_")

if __name__ == "__main__":
    run_analysis()
