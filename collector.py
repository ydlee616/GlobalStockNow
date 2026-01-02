#!/usr/bin/env python3
# GlobalStockNow AI Analyzer v0.1 (2026.1.2)
# Qwen2.5-7B로 해외 속보 → 한국 시장 영향 분석

import json
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# 분석 결과 저장 리스트
analyzed_news = []

# 프롬프트 템플릿 (사업계획서 기반)
PROMPT_TEMPLATE = """
너는 한국 주식 전문가이자 글로벌 경제 분석가다.
아래 해외 속보를 분석해서 한국 시장에 미치는 영향을 10점 만점으로 평가해줘.

뉴스 제목: {title}
뉴스 요약: {summary}
발행 시간: {published}

다음 JSON 형식으로만 답변해 (설명 없이 JSON만 출력):
{{
  "impact_score": 0~10 (숫자만, 한국 시장 영향도. 7점 미만은 분석 제외),
  "impact_period": "단기(1~3일)" 또는 "중기(1~4주)" 또는 "장기(1개월 이상)",
  "related_korean_stocks": ["종목명1", "종목명2", ...] (최대 3개),
  "key_points": "한국 투자자에게 중요한 시사점 한 문장 (30자 이내)"
}}

분석 시작:
"""

print("🧠 GlobalStockNow AI 분석 시작! Qwen2.5-7B 로딩 중...")

# Qwen2.5-7B 4bit quantization (GitHub Actions GPU 지원 없음 → CPU 모드, 첫 실행 2~3분 소요)
model_name = "Qwen/Qwen2.5-7B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto",
    load_in_4bit=True  # 메모리 절약
)

print("✅ 모델 로딩 완료! 분석 시작")

# breaking_news.json 읽기
try:
    with open('breaking_news.json', 'r', encoding='utf-8') as f:
        news_list = json.load(f)
    print(f"📥 {len(news_list)}개 속보 로드 완료")
except:
    print("❌ breaking_news.json 파일 없음. collector 먼저 실행 필요")
    exit()

# 하나씩 분석
for idx, item in enumerate(news_list, 1):
    print(f"\n[{idx}/{len(news_list)}] 분석 중: {item['title'][:60]}...")
    
    prompt = PROMPT_TEMPLATE.format(
        title=item['title'],
        summary=item.get('summary', '요약 없음'),
        published=item['published']
    )
    
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=200,
            temperature=0.3,
            do_sample=False
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    response = response[len(prompt):].strip()  # 프롬프트 제거
    
    try:
        result = json.loads(response)
        if result.get("impact_score", 0) >= 7:
            result["original_title"] = item["title"]
            result["original_link"] = item["link"]
            result["analyzed_at"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
            analyzed_news.append(result)
            print(f"   ✅ 영향도 {result['impact_score']}점 → 분석 저장")
        else:
            print(f"   ⏩ 영향도 {result.get('impact_score', 0)}점 → 스킵")
    except:
        print("   ❌ JSON 파싱 실패 → 스킵")

# 결과 저장
final_count = len(analyzed_news)
print(f"\n🎯 최종 분석 완료: {final_count}개 고영향 속보 선별!")

with open('analyzed_news.json', 'w', encoding='utf-8') as f:
    json.dump(analyzed_news, f, indent=2, ensure_ascii=False)

print("💾 analyzed_news.json 저장 완료 → 콘텐츠 생성 준비 OK!")
