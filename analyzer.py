import os
import requests
import json
import sys

# ==========================================
# [시스템 진단 모드]
# ==========================================
print("🚀 [System Diagnosis] 시스템 점검을 시작합니다...")

# 1. API Key 검사
api_key = os.environ.get("GOOGLE_API_KEY", "")

if not api_key:
    print("❌ [FATAL] GOOGLE_API_KEY가 없습니다. Secrets 설정을 확인하세요.")
    sys.exit(1)

print(f"✅ API Key 발견 (길이: {len(api_key)}자)")
print(f"   - 시작: {api_key[:4]}...")
print(f"   - 끝: ...{api_key[-4:]}")

# 공백 검사
if api_key.strip() != api_key:
    print("⚠️ [WARNING] 키 앞뒤에 공백(스페이스바)이 감지되었습니다! GitHub Secrets에서 공백을 지워주세요.")
else:
    print("✅ 키 형식 정상 (공백 없음)")

# 2. 라이브러리 없이 직접 통신 테스트 (Raw Request)
# Gemini 1.5 Flash 모델에 직접 '안녕'이라고 인사를 건네봅니다.
print("\n📡 [Network Test] Google 서버에 직접 접속을 시도합니다...")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key.strip()}"
headers = {'Content-Type': 'application/json'}
data = {
    "contents": [{"parts": [{"text": "Hello, are you working?"}]}]
}

try:
    response = requests.post(url, headers=headers, json=data)
    
    print(f"   - 상태 코드: {response.status_code}")
    
    # 결과 분석
    if response.status_code == 200:
        print("🎉 [SUCCESS] 연결 성공! API 키와 모델이 정상 작동 중입니다.")
        print(f"   - 응답: {response.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No text')}")
    else:
        print("❌ [FAIL] 연결 실패. 구글 서버의 에러 메시지는 다음과 같습니다:")
        print("="*40)
        print(response.text)  # 에러의 진짜 이유가 여기에 나옵니다
        print("="*40)
        
        # 404 에러일 경우 추가 가이드
        if response.status_code == 404:
            print("💡 [Tip] 404 에러는 '키는 맞지만, 이 프로젝트에서 Gemini API 사용이 활성화되지 않았음'을 의미할 수 있습니다.")

except Exception as e:
    print(f"❌ [CRITICAL] 통신 오류 발생: {e}")

print("\n🏁 [Diagnosis] 진단 종료.")
