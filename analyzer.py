"""
Module: analyzer.py | Version: 0.3.2 | Updated: 2026-01-10
Description: Safe JSON parsing & Per-article Exception handling.
"""
import json, time, requests, os, re, torch
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RUN_NUMBER = os.environ.get("GITHUB_RUN_NUMBER", "Local")
INPUT_FILE = 'breaking_news.json'

def safe_send_telegram(msg, article_id=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    if article_id is not None:
        payload["reply_markup"] = json.dumps({"inline_keyboard": [[{"text": "🎬 유튜브 시나리오 생성 (학습)", "callback_data": f"select_{article_id}"}]]})
    try: requests.post(url, data=payload, timeout=10)
    except: pass

def clean_data(text):
    return re.sub(r'<.*?>', '', text)

# 엔진 로드
print(f"📂 [Ver 0.3.2] AI Engine Loading...")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct", torch_dtype="auto", device_map="cpu")

def analyze_strategic(article):
    # 정화된 요약문 사용
    summary = clean_data(article.get('summary', ''))
    prompt = f"[Financial Analysis Only] Analyze news for KOSPI/KOSDAQ impact. Output KOREAN JSON.\nNews: {article.get('title')} - {summary}"
    
    # [1. Gemini 시도]
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}, timeout=30)
        if res.status_code == 200:
            text = res.json()['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(re.sub(r'```json|```', '', text).strip())
            data['engine'] = 'Gemini_Pro'
            return data
    except: pass

    # [2. Qwen Rescue 시도]
    try:
        inputs = tokenizer(f"<|im_start|>system\n금융 분석가로서 한글 JSON 보고서를 작성하세요.<|im_end|>\n<|im_start|>user\n{article.get('title')}<|im_end|>\n<|im_start|>assistant\n", return_tensors="pt")
        outputs = model.generate(**inputs, max_new_tokens=512)
        text = tokenizer.decode(outputs[0], skip_special_tokens=True).split("assistant")[-1]
        data = json.loads(re.search(r'\{.*\}', text, re.DOTALL).group())
        data['engine'] = 'Qwen_Rescue'
        return data
    except: return None

def run():
    if not os.path.exists(INPUT_FILE): return
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    results_count = 0
    for i, art in enumerate(articles[:15]):
        # [과거 데이터 필터링]
        if any(year in art.get('published_at', '') for year in ['2018', '2019']): continue

        try:
            res = analyze_strategic(art)
            if res:
                # [안전한 데이터 접근] Ver 0.3.2 핵심 로직
                title = res.get('title', '제목 없음')
                score = res.get('score', 0)
                # 데이터 타입 체크로 AttributeError 원천 차단
                essence = res.get('essence', {}) if isinstance(res.get('essence'), dict) else {}
                subtext = essence.get('subtext', '행간 분석중')
                
                maps = res.get('map', {}) if isinstance(res.get('map'), dict) else {}
                stocks = maps.get('stocks', []) if isinstance(maps.get('stocks'), list) else []
                
                msg = f"{'💎' if res.get('engine')=='Gemini_Pro' else '⚔️'} **1. 제목: {title}**\n**2. 매체**: {art.get('source')}\n**3. 영향도 ({score}점)**: {subtext}\n**4. 관련주**: {', '.join(stocks) if stocks else '분석중'}"
                safe_send_telegram(msg, i)
                results_count += 1
        except Exception as e:
            print(f"⚠️ {i}번 기사 스킵 (오류: {e})")
            continue
        time.sleep(35)

    if results_count == 0:
        safe_send_telegram(f"🌍 **글로벌스톡나우 속보 브리핑 (#{RUN_NUMBER})**\n\n현재 분석된 유효 속보 없음\n_AI 정밀 분석 완료_")

if __name__ == "__main__": run()
