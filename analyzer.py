#!/usr/bin/env python3
# GlobalStockNow AI Analyzer v0.2 (2026.1.2)
# Qwen2.5-1.5B-Instruct로 해외 속보 → 한국 시장 영향 분석
# 나중에 고품질 원하시면 model_name만 "Qwen/Qwen2.5-7B-Instruct"로 바꾸세요

import json
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# 분석된 뉴스 저장 리스트
analyzed_news = []

# 프롬프트 템플릿 (사업계획서 페이지 9 기반)
PROMPT_TEMPLATE = """
너는 한국 주식 전문가이자 글로벌 경제 분석가다.
아래 해외 속보를 분석해서 한국 시장에 미치는 영향을 10점 만점으로 평가해줘.

뉴스 제목: {title}
뉴스 요약: {summary}
발행 시간: {published}

다음 JSON 형식으로만 답변해 (설명 없이 JSON만 출력):
{
  "impact_score": 0.0 ~ 10.0 (숫자, 한국 시장 영향도. 7.0점 미만은 분석 제외),
  "impact_period": "단기(1~3일)" 또는 "중기(1~4주)" 또는 "장기(1개월 이상)",
  "related_korean_stocks": ["종목명1", "종목명2", ...] (최대 3개, 한국 상장사만),
  "key_points": "한국 투자자에게 중요한 시사점 한 문장 (30자 이내)"
}

분석 시작:
"""

print("🧠 GlobalStockNow AI 분석 시작! Qwen2.5 모델 로딩 중...")

# 모델 선택 (빠른 테스트용 1.5B, 고품질 원할 때 7B로 변경)
model_name = "Qwen/Qwen2.5-1.5B-Instruct"   # ← 여기만 바꾸면 됨

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto",
    load_in_4bit=True   # 메모리 절약 (CPU에서도 가능)
)

print("✅ 모델 로딩 완료! 분석 시작")

# breaking_news.json 읽기
try:
    with open('breaking_news.json', 'r', encoding='utf-8') as f:
        news_list = json.load(f)
    print(f"📥 {len(news_list)}개 속보 로드 완료")
except FileNotFoundError:
    print("❌ breaking_news.json 파일이 없습니다. collector.py를 먼저 실행해주세요.")
    exit()
except Exception as e:
    print(f"❌ 파일 읽기 오류: {e}")
    exit()

# 개별 뉴스 분석
for idx, item in enumerate(news_list, 1):
    print(f"\n[{idx}/{len(news_list)}] 분석 중: {item['title'][:70]}...")
    
    prompt = PROMPT_TEMPLATE.format(
        title=item['title'],
        summary=item.get('summary', '요약 없음')[:500],
        published=item['published']
    )
    
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=200,
            temperature=0.3,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # 프롬프트 부분 제거
    response = response[len(prompt):].strip()
    
    try:
        # JSON 파싱 (때때로 모델이 ```json 블록으로 감쌀 수 있음)
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
        result = json.loads(response)
        
        score = float(result.get("impact_score", 0))
        if score >= 7.0:
            result["original_title"] = item["title"]
            result["original_link"] = item["link"]
            result["analyzed_at"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
            analyzed_news.append(result)
            print(f"   ✅ 영향도 {score:.1f}점 → 저장")
        else:
            print(f"   ⏩ 영향도 {score:.1f}점 → 스킵 (7점 미만)")
    except json.JSONDecodeError:
        print("   ❌ JSON 파싱 실패 → 스킵")
    except Exception as e:
        print(f"   ❌ 분석 오류: {e} → 스킵")

# 최종 결과 저장
final_count = len(analyzed_news)
print(f"\n🎯 최종 분석 완료: {final_count}개 고영향 속보 선별!")

with open('analyzed_news.json', 'w', encoding='utf-8') as f:
    json.dump(analyzed_news, f, indent=2, ensure_ascii=False)

print("💾 analyzed_news.json 저장 완료 → 다음 단계(콘텐츠 생성) 준비 OK!")
