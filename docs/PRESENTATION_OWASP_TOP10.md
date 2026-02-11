# OWASP Top 10:2025 취약점 실습 발표 자료
### 공공 의료 민원 포털 기반 보안 취약점 분석 및 실습

---

## 슬라이드 1. 프로젝트 소개

### 공공 의료 민원 포털

> 교육 목적으로 의도적 취약점을 포함한 3-Tier 웹 애플리케이션

| Tier | 기술 | 역할 |
|------|------|------|
| Web | Nginx | 리버스 프록시 (HTTP, 포트 8080) |
| WAS | Flask (Python) | 비즈니스 로직, REST API |
| DB | MariaDB + SQLAlchemy | 데이터 저장 |

**주요 기능**
- 회원 가입 / 로그인 / 마이페이지
- 민원 접수 및 상태 조회
- 커뮤니티 게시판 / 공지사항
- 관리자 대시보드 / 감사 로그
- **취약점 실습 랩 (`/vulnlab/`) — OWASP A01~A10 전 항목**

---

## 슬라이드 2. OWASP Top 10:2025 전체 구성

| # | 코드 | 카테고리 | 구현 시나리오 수 |
|---|------|---------|----------------|
| 1 | A01 | Broken Access Control | 2개 |
| 2 | A02 | Security Misconfiguration | 1개 |
| 3 | A03 | Software Supply Chain Failures | 1개 |
| 4 | A04 | Cryptographic Failures | 2개 |
| 5 | A05 | Injection | 1개 |
| 6 | A06 | Insecure Design | 1개 |
| 7 | A07 | Authentication Failures | 2개 |
| 8 | A08 | Software or Data Integrity Failures | 1개 |
| 9 | A09 | Security Logging and Alerting Failures | 1개 |
| 10 | A10 | Mishandling of Exceptional Conditions | 1개 |
| | | **합계** | **13개 시나리오** |

---

## 슬라이드 3. A01 — Broken Access Control (접근 제어 취약점)

### 정의
인가되지 않은 사용자가 다른 사용자의 데이터 또는 기능에 접근 가능한 취약점

### 시나리오 1: 파일 IDOR (Insecure Direct Object Reference)

**취약 URL**
```
GET /vulnlab/crypto3/download?file_name=진료기록_홍길동_900101.pdf
```

**문제점**
```python
# 소유권 확인 없이 파일명만으로 다운로드 허용
file_name = request.args.get("file_name", "")
content = _FAKE_PATIENT_FILES.get(file_name)
# ← 요청자가 해당 파일의 주인인지 전혀 확인하지 않음
```

**노출 정보**: 타인의 주민번호, 진료 기록, 처방 내역

**대응 방안**
```python
# 파일 소유자와 현재 로그인 사용자 일치 여부 확인
if file.owner_id != current_user.id:
    abort(403)
```

---

### 시나리오 2: @login_required 누락

**취약 URL**
```
GET /vulnlab/auth3/user-list  ← 로그인 없이 접근 가능
```

**문제점**
```python
@app.route("/vulnlab/auth3/user-list")
# @login_required  ← 의도적 누락
def vulnlab_auth3_userlist():
    users = User.query.all()   # 전체 사용자 정보 반환
```

**노출 정보**: 전체 사용자 ID, username, email, 전화번호, role

**대응 방안**
```python
@app.route("/admin/user-list")
@login_required
@admin_required
def admin_user_list():
    ...
```

---

## 슬라이드 4. A02 — Security Misconfiguration (보안 설정 오류)

### 정의
기본값 유지, 불필요한 기능 활성화, 상세 에러 노출 등 잘못된 보안 설정

### 시나리오: 설정 정보 + 상세 에러 노출

**취약 URL**
```
GET  /vulnlab/a02          ← 설정 테이블 표시
GET  /vulnlab/a02?trigger_error=1  ← Traceback 노출
```

**노출 정보**

| 항목 | 노출값 | 위험도 |
|------|--------|--------|
| SECRET_KEY | `dev-secret` | 세션 위조 가능 |
| DEBUG | `True` | 운영 환경 노출 |
| DATABASE_URL | `sqlite:///instance/app.db` | DB 경로 노출 |
| Traceback | 파일 경로 + 코드 줄 번호 | 내부 구조 노출 |

**대응 방안**
```python
# 운영 환경 설정
SECRET_KEY = os.environ["SECRET_KEY"]  # 환경변수로 분리
DEBUG = False
# 에러 핸들러에서 일반 메시지만 반환
@app.errorhandler(500)
def internal_error(e):
    return render_template("500.html"), 500
```

---

## 슬라이드 5. A03 — Software Supply Chain Failures (소프트웨어 공급망 취약점)

### 정의
사용하는 라이브러리, 패키지, 의존성의 무결성 미검증으로 인한 취약점

### 시나리오: 버전 미고정 패키지

**취약 URL**
```
GET /vulnlab/a03
```

**문제점**
```
# requirements.txt 예시
flask          # ← 버전 미고정
requests       # ← 버전 미고정
sqlalchemy     # ← 버전 미고정
```

**위험**: 악성 코드가 포함된 버전으로 자동 업데이트 가능

**대응 방안**
```
# 안전한 requirements.txt
flask==3.0.3
requests==2.31.0
sqlalchemy==2.0.29
# pip-audit, safety 등 취약점 스캐너 정기 실행
```

---

## 슬라이드 6. A04 — Cryptographic Failures (암호화 실패)

### 정의
민감 데이터를 평문으로 전송하거나 취약한 암호화 알고리즘 사용

### 시나리오 1: HTTP 평문 전송

**구조**: Nginx가 HTTPS 미설정 → 민원 접수 폼 데이터가 평문 전송

```
POST /complaints/new HTTP/1.1
Host: localhost:8080
Content-Type: application/x-www-form-urlencoded

title=진료비+환급+요청&patient_name=홍길동
&resident_number=900101-1234567&medical_record=고혈압+진단
&content=...
```

**Burp Suite로 캡처 시** — 주민번호, 이름, 진료 기록 등 민감 정보 평문 노출

**대응 방안**
- TLS 인증서 적용 (HTTPS)
- HSTS 헤더 설정
- Nginx에서 HTTP → HTTPS 리다이렉트

---

### 시나리오 2: MD5 해시 저장 + SQL Injection으로 탈취

**취약 URL**
```
GET /vulnlab/crypto2?q=' UNION SELECT username,password_hash,email,role,'x' FROM user --
```

**MD5 해시 예시**

| 사용자 | MD5 해시 | 원문 비밀번호 |
|--------|---------|-------------|
| admin_demo | `0192023a7bbd73250516f069df18b500` | admin1234 |
| user1_demo | `a9af47aba5d87a79bb9ce7dfc11e70f5` | user12345 |

**문제**: MD5는 레인보우 테이블로 수초 내 원문 복원 가능

**대응 방안**
```python
# 취약 (MD5)
hashlib.md5(password.encode()).hexdigest()

# 안전 (bcrypt/PBKDF2)
from werkzeug.security import generate_password_hash
generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
```

---

## 슬라이드 7. A05 — Injection (인젝션)

### 정의
공격자가 입력한 데이터가 명령 또는 쿼리의 일부로 해석되는 취약점

### 시나리오: SQL Injection

**취약 URL**
```
GET /vulnlab/a05?q=' OR '1'='1
GET /vulnlab/a05?q=' UNION SELECT id,username,password_hash,email,role FROM user --
```

**취약한 코드**
```python
# f-string으로 사용자 입력을 SQL에 직접 삽입
vuln_sql = f"SELECT id,username,email,role FROM user WHERE username LIKE '%{search}%'"
rows = db.session.execute(text(vuln_sql)).fetchall()
```

**공격 결과**

| 페이로드 | 결과 |
|---------|------|
| `' OR '1'='1` | 전체 사용자 조회 |
| `' UNION SELECT ... FROM user --` | password_hash 탈취 |
| `'; DROP TABLE user --` | 테이블 삭제 |

**대응 방안 — 파라미터 바인딩**
```python
# 안전한 쿼리 (파라미터 바인딩)
safe_sql = "SELECT id,username,email,role FROM user WHERE username LIKE :s"
rows = db.session.execute(text(safe_sql), {"s": f"%{search}%"}).fetchall()
```

---

## 슬라이드 8. A06 — Insecure Design (안전하지 않은 설계)

### 정의
설계 단계에서 보안 요구사항이 누락되어 발생하는 구조적 취약점

### 시나리오: Rate Limiting 부재 + 상태 전이 검증 없음

**취약 URL**
```
POST /vulnlab/a06  (반복 요청 가능)
POST /vulnlab/a06  action=change_status  (상태 전이 규칙 미적용)
```

**Rate Limiting 부재**
```python
# 요청 횟수를 기록하지만 차단하지 않음
_vulnlab_a06_request_log.setdefault(ip, []).append(time.time())
# ← 아무리 많이 요청해도 차단 없음
```

**상태 전이 검증 부재**
```
정상 흐름: received → in_review → resolved / rejected
취약점:    received → resolved  (중간 단계 건너뜀 가능)
```

**대응 방안**
```python
# Rate Limiting
from flask_limiter import Limiter
@limiter.limit("5 per minute")

# 상태 전이 검증
VALID_TRANSITIONS = {
    "received": ["in_review"],
    "in_review": ["resolved", "rejected"],
}
if new_status not in VALID_TRANSITIONS.get(current_status, []):
    abort(400)
```

---

## 슬라이드 9. A07 — Authentication Failures (인증 실패)

### 정의
인증 메커니즘이 잘못 구현되어 공격자가 타인의 계정을 탈취할 수 있는 취약점

### 시나리오 1: 브루트포스 공격 (계정 잠금 없음)

**취약 URL**
```
POST /login  (무제한 반복 가능)
```

**문제점**: 로그인 실패 횟수 제한 없음, 계정 잠금 없음, CAPTCHA 없음

```python
# 현재 코드 — 실패해도 아무 제한 없음
if not check_password_hash(user.password_hash, password):
    flash("비밀번호가 올바르지 않습니다.", "danger")
    return render_template("auth/login.html")
    # ← 잠금 처리 없음
```

---

### 시나리오 2: 순차 세션 ID 추측 공격

**취약 URL**
```
GET /vulnlab/auth2/profile?session_id=1
GET /vulnlab/auth2/profile?session_id=2
```

**취약한 세션 발급**
```python
# 카운터 기반 순차 세션 ID
_weak_session_counter[0] += 1
sid = _weak_session_counter[0]   # 1, 2, 3, 4...

# 공격자는 숫자만 바꾸면 타인 세션 탈취 가능
```

**대응 방안**
```python
import secrets

# 암호학적으로 안전한 랜덤 토큰 (256bit)
session_token = secrets.token_urlsafe(32)
# 예: "3d9Xk-mQr8vBcZ1wNpTjL..."

resp.set_cookie("session", session_token,
                httponly=True, secure=True, samesite="Strict")
```

---

## 슬라이드 10. A08 — Software or Data Integrity Failures (무결성 실패)

### 정의
소프트웨어 업데이트, 데이터, CI/CD 파이프라인의 무결성을 검증하지 않아 발생하는 취약점

### 시나리오: Pickle 역직렬화를 통한 임의 코드 실행 (RCE)

**취약 URL**
```
POST /vulnlab/a08   action=vuln_deserialize  b64_input=[페이로드]
```

**취약한 코드**
```python
# 사용자 입력을 검증 없이 pickle로 역직렬화
raw = base64.b64decode(b64_input)
obj = pickle.loads(raw)  # ← 임의 코드 실행 가능!
```

**공격 페이로드 생성**
```python
import pickle, base64, os

class Exploit(object):
    def __reduce__(self):
        return (os.system, ("id",))  # 서버에서 'id' 명령 실행

payload = base64.b64encode(pickle.dumps(Exploit())).decode()
print(payload)   # → 이 값을 폼에 붙여넣으면 RCE 발생
```

**대응 방안**
```python
# pickle 대신 JSON 사용 (코드 실행 불가)
import json
obj = json.loads(user_input)
```

---

## 슬라이드 11. A09 — Security Logging and Alerting Failures (로깅 실패)

### 정의
보안 이벤트가 기록되지 않거나, 민감 정보가 로그에 평문으로 저장되거나, 이상 징후 알림이 없는 취약점

### 시나리오: 평문 비밀번호 로깅 + 알림 부재

**취약 URL**
```
POST /vulnlab/a09
```

**취약한 코드**
```python
# AuditLog.meta에 비밀번호 평문 저장
log_action(
    "vulnlab_sensitive_log",
    meta={
        "password_plaintext": fake_password,  # ← 평문!
        "user": current_user.username,
    },
)
```

**데이터베이스에서 조회 시**
```sql
SELECT meta FROM audit_log WHERE action = 'vulnlab_sensitive_log';
-- 결과: {"password_plaintext": "admin1234", "user": "admin"}
```

**문제점**
- 로그 파일 탈취 시 비밀번호 즉시 노출
- 로그인 실패 100회 이상 발생해도 관리자 알림 없음
- 이상 행위 탐지(SIEM) 미연동

**대응 방안**
```python
# 비밀번호 마스킹 후 기록
log_action("login_attempt", meta={"password": "****"})

# 임계치 초과 시 알림 발송
if fail_count >= 5:
    send_alert(f"[보안 경고] {username} 계정 로그인 실패 {fail_count}회")
```

---

## 슬라이드 12. A10 — Mishandling of Exceptional Conditions (예외 처리 오류)

### 정의
예외 상황을 잘못 처리하여 보안 제어가 우회되거나 내부 정보가 노출되는 취약점

### 시나리오 1: Fail-Open 설계 (admin_required 비활성)

**문제**: 권한 검증 코드가 주석 처리됨 → 일반 사용자도 관리자 기능 접근

```python
def admin_required(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        # ↓ 권한 체크 코드가 주석 처리되어 모든 요청 통과
        # if current_user.role != "admin":
        #     return redirect(url_for("index"))
        return func(*args, **kwargs)   # ← 항상 실행!
    return wrapped
```

**결과**: `GET /admin` → 로그인만 되어 있으면 누구나 접근 가능

---

### 시나리오 2: Traceback 전체 노출

**취약 URL**
```
POST /vulnlab/a10   action=divide  divisor=0
```

**취약한 코드**
```python
try:
    result = 100 / int(divisor_str)
except ZeroDivisionError:
    import traceback
    vuln_result = traceback.format_exc()  # ← 전체 스택 화면에 출력
```

**노출 정보**
```
Traceback (most recent call last):
  File "/app/routes.py", line 1384, in vulnlab_a10
    result = 100 / divisor
ZeroDivisionError: division by zero
```

→ 소스 파일 경로, 함수명, 코드 줄 번호 노출

**대응 방안**
```python
# Fail-Secure: 예외 발생 시 접근 차단
def admin_required(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            if current_user.role != "admin":
                abort(403)
        except Exception:
            abort(403)   # ← 예외 발생 시도 거부 (Fail-Secure)
        return func(*args, **kwargs)

# 에러 메시지: 내부 정보 숨김
except Exception:
    return "처리 중 오류가 발생했습니다.", 500
```

---

## 슬라이드 13. 전체 공격 실습 흐름

```
[사전 준비]
  - docker compose up --build
  - Burp Suite 프록시 설정 (127.0.0.1:8080)
  - user1 / user12345 로그인

[실습 순서]

Step 1  A10  Fail-Open + Traceback
        → /admin 직접 접속, /vulnlab/a10 에서 0 입력

Step 2  A02  설정 정보 노출
        → /vulnlab/a02, ?trigger_error=1

Step 3  A01  인증 누락 사용자 목록
        → 로그아웃 후 /vulnlab/auth3/user-list 직접 입력

Step 4  A07  순차 세션 ID 추측
        → /vulnlab/auth2 에서 로그인 → session_id=1 변경

Step 5  A01  파일 IDOR
        → /vulnlab/crypto3 → 파일명 변경 다운로드

Step 6  A04  HTTP 평문 전송
        → Burp Suite + /complaints/new 민원 접수
        → 주민번호, 진료기록 평문 캡처

Step 7  A05  SQL Injection
        → /vulnlab/a05?q=' OR '1'='1
        → /vulnlab/a05?q=' UNION SELECT ... --

Step 8  A04  MD5 + SQL Injection 연계
        → /vulnlab/crypto2 → hash 탈취 → crackstation.net 복원

Step 9  A07  브루트포스 무제한 시도
        → /vulnlab/a07 → 공통 비밀번호 목록 입력

Step 10 A06  Rate Limiting 부재
        → /vulnlab/a06 → 반복 클릭 → 횟수 증가 확인

Step 11 A08  Pickle RCE
        → /vulnlab/a08 → 안전 페이로드 생성 → 취약 폼 붙여넣기

Step 12 A09  평문 로깅
        → /vulnlab/a09 → 비밀번호 입력 → DB 로그 확인

Step 13 A03  취약 패키지 스캔
        → /vulnlab/a03 → pip list + requirements.txt 확인
```

---

## 슬라이드 14. 취약점 대응 방안 요약

| OWASP | 취약점 | 핵심 대응 방안 |
|-------|--------|--------------|
| A01 | IDOR / 인증 누락 | 소유권 검증 + `@login_required` + `@admin_required` |
| A02 | 설정 정보 노출 | 환경변수 분리 + DEBUG=False + 커스텀 에러 페이지 |
| A03 | 공급망 취약점 | 버전 고정 + pip-audit / safety 정기 스캔 |
| A04 | 약한 암호화 / 평문 전송 | HTTPS(TLS) + bcrypt / PBKDF2 사용 |
| A05 | SQL Injection | 파라미터 바인딩 + ORM 사용 + 입력 검증 |
| A06 | 설계 취약점 | Rate Limiting + 상태 전이 규칙 적용 |
| A07 | 인증 실패 | 계정 잠금 + MFA + 암호학적 랜덤 세션 ID |
| A08 | 무결성 실패 | pickle 금지 + JSON 사용 + 서명 검증 |
| A09 | 로깅 실패 | 민감 정보 마스킹 + SIEM 연동 + 임계치 알림 |
| A10 | 예외 처리 오류 | Fail-Secure + 내부 에러 숨김 + 에러 핸들러 |

---

## 슬라이드 15. 결론

### 핵심 메시지

> "보안 취약점은 코드 한 줄, 설정 하나에서 시작된다"

**이 프로젝트에서 배운 것**

1. OWASP Top 10은 추상적인 분류가 아닌, 실제 코드에서 재현 가능한 취약점
2. 취약한 코드와 안전한 코드의 차이는 구조적으로 단순하지만 파급력이 크다
3. 의료 정보, 주민번호와 같은 민감 데이터는 설계 단계부터 보호 방안을 고려해야 한다
4. 단일 취약점보다 복합 공격(A04 + A05: MD5 + SQLi 연계)이 실제 피해를 키운다

### 프로젝트 구성 수치

| 항목 | 수치 |
|------|------|
| OWASP 카테고리 구현 | 10 / 10 (100%) |
| 구체적 공격 시나리오 | 13개 |
| vulnlab 라우트 | 17개 |
| 취약 기술 스택 | pickle, MD5, raw SQL, 순차 세션 ID, 평문 전송 등 |
| 데모 가짜 의료 데이터 | 4명 (주민번호 + 진료 기록 포함) |

---

*이 문서는 교육 목적으로 작성되었습니다. 실제 시스템에 대한 무단 공격은 불법입니다.*
