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

def send_telegram_with_button(message, article_id):
    """보스의 선택을 위한 버튼이 포함된 텔레그램 메시지 발송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # [🎬 유튜브 시나리오 생성] 버튼 추가
    # 실제 구현 시 버튼 클릭을 수신할 서버 URL이나 GitHub Dispatch를 연결할 수 있습니다.
    inline_keyboard = {
        "inline_keyboard": [[
            {
                "text": "🎬 이 뉴스로 유튜브 시나리오 생성",
                "callback_data": f"create_video_{article_id}"
            }
        ]]
    }
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(inline_keyboard)
    }
    
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"텔레그램 발송 오류: {e}")

# ==========================================
# 1. AI 분석 엔진 (8단계 초정밀 분석 프롬프트 적용)
# ==========================================
print("📂 로컬 수색대(Qwen2.5-0.5B) 상시 대기 중...")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct", torch_dtype="auto", device_map="cpu")

def call_strategic_ai(article):
    # 보강된 8단계 정밀 분석 프롬프트 [cite: 2026-01-09]
    prompt = f"""당신은 글로벌 매크로 분석가이자 한국 주식시장 헤지펀드 리서치 디렉터입니다. 
다음 해외 뉴스를 바탕으로 8단계 정밀 분석을 수행하여 JSON으로 출력하십시오.

[분석 지침]:
1. 뉴스의 본질/배경: 핵심 요약 및 행간의 의도(Subtext)
2. 직접적 영향: 관련 기업 및 국가 증시 타격/수혜
3. 간접적 영향: 환율(원/달러), 원자재(석유/금), 글로벌 공급망 및 지정학 리스크
4. 투자자 심리: 기대와 우려 사항, 변동성 확대 가능성
5. 과거 유사 사례 비교: 과거의 비슷한 사건 소환 및 현재와의 차이점 분석
6. 시간축별 영향: 단기(1-5일), 중기(1-3월), 장기(6월 이상) 전망
7. 업종/종목 후보: 수혜/리스크 업종 TOP 3 및 변동성 노출 종목
8. 투자 전략: 긍정/부정 시나리오 및 투자자 유형별 조언

[출력 JSON 구조]:
{{
  "title": "제목", "essence": {{ "subtext": "", "type": "" }},
  "direct": "", "indirect": {{ "fx": "", "commodities": "", "geopolitics": "" }},
  "sentiment": {{ "psychology": "", "volatility": "" }},
  "history": {{ "case": "", "comparison": "" }},
  "timeline": {{ "short": "", "mid": "", "long": "" }},
  "map": {{ "sectors": {{ "up": [], "down": [] }}, "stocks": [] }},
  "strategy": {{ "scenarios": "", "action": "" }},
  "score": 0.0
}}

뉴스 제목: {article.get('title')}
뉴스 내용: {article.get('summary')}
"""
    # 1. Gemini Pro 시도
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}, timeout=30)
        if res.status_code == 200:
            text = res.json()['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(re.sub(r'```json|```', '', text).strip())
            data['engine'] = 'Gemini_Pro'
            return data
    except: pass

    # 2. 실패 시 Qwen Rescue 시도
    print(f"   ⚔️ Qwen Rescue 투입: {article.get('title')[:15]}...")
    inputs = tokenizer(f"<|im_start|>system\n글로벌 경제 분석가로서 JSON 한글 분석을 수행하세요.<|im_end|>\n<|im_start|>user\n{article.get('title')}<|im_end|>\n<|im_start|>assistant\n", return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=512)
    try:
        text = tokenizer.decode(outputs[0], skip_special_tokens=True).split("assistant")[-1]
        data = json.loads(re.search(r'\{.*\}', text, re.DOTALL).group())
        data['engine'] = 'Qwen_Rescue'
        return data
    except: return None

# ==========================================
# 3. 자율 실행 및 리포트 생성
# ==========================================
def orchestrate():
    if not os.path.exists(INPUT_FILE): return
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f).get('articles', [])

    if not articles:
        return

    results = []
    # 전략 키워드 중심 상위 10건 분석
    for i, art in enumerate(articles[:10]):
        res = call_strategic_ai(art)
        if res:
            res['original_source'] = art.get('source')
            results.append(res)
            
            # 텔레그램으로 즉시 개별 보고 (5단계 보강 양식)
            icon = "💎" if res.get('engine') == 'Gemini_Pro' else "⚔️"
            msg = f"{icon} **1. 제목: {res.get('title')}**\n"
            msg += f"**2. 매체**: {res.get('original_source')}\n"
            msg += f"**3. 영향도 ({res.get('score')}점)**: {res['essence'].get('subtext', '행간 분석중')}\n"
            msg += f"   - **간접영향**: 환율({res['indirect'].get('fx')}), 원자재({res['indirect'].get('commodities')})\n"
            msg += f"**4. 영향받는 주식**: {', '.join(res['map'].get('stocks', []))}\n"
            msg += f"**5. 과거사례**: {res['history'].get('case')}\n"
            msg += f"\n**💡 분석가 제언**: {res['strategy'].get('action')}"
            
            send_telegram_with_button(msg, i)
        
        time.sleep(35) # 과속 방지

if __name__ == "__main__":
    orchestrate()
