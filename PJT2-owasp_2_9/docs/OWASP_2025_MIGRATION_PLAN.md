# OWASP Top 10: 2021 → 2025 마이그레이션 계획

## 1. 개요

본 문서는 현재 OWASP Top 10:2021 기반으로 구현된 보안 시나리오를 2025 버전으로 업데이트하기 위한 계획을 정의한다.

**목표**: 교육용 취약점 시나리오를 OWASP Top 10:2025에 맞게 재구성

## 2. 버전 비교 분석

### 2.1 2021 vs 2025 매핑표

| 2021 버전 | 2025 버전 | 변경 사항 |
|-----------|-----------|-----------|
| A01: Broken Access Control | A01: Broken Access Control | 유지 |
| A05: Security Misconfiguration | A02: Security Misconfiguration | 순위 상승 (5→2) |
| A06: Vulnerable and Outdated Components | A03: Software Supply Chain Failures | **신규 통합 확장** |
| A02: Cryptographic Failures | A04: Cryptographic Failures | 순위 하락 (2→4) |
| A03: Injection | A05: Injection | 순위 하락 (3→5) |
| A04: Insecure Design | A06: Insecure Design | 순위 하락 (4→6) |
| A07: Identification and Authentication Failures | A07: Authentication Failures | 명칭 간소화 |
| A08: Software and Data Integrity Failures | A08: Software or Data Integrity Failures | 유지 |
| A09: Security Logging and Monitoring Failures | A09: Security Logging and Alerting Failures | 명칭 변경 (Monitoring→Alerting) |
| A10: Server-Side Request Forgery | A10: Mishandling of Exceptional Conditions | **완전 교체** |

### 2.2 주요 변경 사항

#### 신규 항목
1. **A03: Software Supply Chain Failures**
   - 기존 A06(Vulnerable Components)을 확장
   - CI/CD 파이프라인, SBOM, 의존성 관리 포함
   - 2024~2025 공급망 공격 급증 반영

2. **A10: Mishandling of Exceptional Conditions**
   - SSRF 대체
   - 예외 처리 실패, Fail Open, 에러 핸들링 부재 포함
   - 24개 CWE 매핑

#### 제거된 항목
- **A10: SSRF** - 별도 항목에서 제외 (A01 또는 A05에서 부분 커버)

## 3. 구현 계획

### 3.1 파일 수정 대상

| 파일 | 수정 내용 |
|------|-----------|
| `was/app/security_catalog.py` | 시나리오 데이터 전체 재작성 |
| `docs/OWASP_SCENARIOS.md` | 문서 업데이트 |
| `was/app/templates/security/list.html` | UI 변경 없음 (데이터만 변경) |
| `was/app/templates/security/detail.html` | UI 변경 없음 (데이터만 변경) |

### 3.2 각 항목별 구현 상세

---

#### A01: Broken Access Control (유지)

**현재 상태**: 구현 완료

**점검 포인트**:
- 비로그인 사용자의 보호 페이지 접근 차단
- 일반 사용자의 `/admin` 접근 차단
- 타인 게시물/민원 수정 및 조회 차단

**취약점 시연 방안**:
- IDOR: `/complaints/{타인_id}` 직접 접근 시도
- 권한 우회: 일반 사용자로 `/admin/users` POST 요청

---

#### A02: Security Misconfiguration (순위 상승)

**현재 상태**: A05로 구현됨 → A02로 변경

**점검 포인트**:
- 디버그 모드 활성화 상태 노출
- 기본 관리자 계정(`admin/admin1234`) 미변경
- 과도한 에러 메시지 노출
- 불필요한 HTTP 헤더 노출

**취약점 시연 방안**:
- `FLASK_ENV=development` 상태에서 에러 스택트레이스 노출
- 기본 계정으로 관리자 로그인

---

#### A03: Software Supply Chain Failures (신규)

**현재 상태**: 미구현 (기존 A06 Vulnerable Components 대체)

**점검 포인트**:
- 의존성 버전 고정 여부 (`requirements.txt`)
- 알려진 취약점이 있는 패키지 사용 여부
- SBOM(Software Bill of Materials) 관리 여부
- CI/CD 파이프라인 보안 설정

**취약점 시연 방안**:
- `pip-audit` 또는 `safety` 도구로 취약점 스캔 결과 제시
- 의존성 트리 시각화 및 취약점 매핑
- 버전 미고정 패키지 식별

**서비스 내 구현**:
```python
# /security/supply-chain-check 엔드포인트 추가 (관리자 전용)
# requirements.txt 파싱 및 취약점 DB 조회 시뮬레이션
```

---

#### A04: Cryptographic Failures (순위 하락)

**현재 상태**: A02로 구현됨 → A04로 변경

**점검 포인트**:
- SECRET_KEY 하드코딩 여부
- 비밀번호 해시 알고리즘 (werkzeug 사용 중)
- 민감 데이터 평문 전송/저장

**취약점 시연 방안**:
- 환경변수 미설정 시 기본 시크릿 사용 확인
- 세션 쿠키 암호화 설정 점검

---

#### A05: Injection (순위 하락)

**현재 상태**: A03으로 구현됨 → A05로 변경

**점검 포인트**:
- SQL Injection (ORM 사용으로 기본 방어)
- Template Injection (Jinja2 autoescaping)
- Command Injection 가능 지점

**취약점 시연 방안**:
- 검색 파라미터에 SQL 구문 삽입 시도 (ORM으로 방어됨을 확인)
- XSS 페이로드 입력 테스트

---

#### A06: Insecure Design (순위 하락)

**현재 상태**: A04로 구현됨 → A06으로 변경

**점검 포인트**:
- 민원 상태 전이 규칙 미검증
- 비즈니스 로직 우회 가능성
- Rate limiting 부재

**취약점 시연 방안**:
- 민원 상태를 `received` → `resolved` 직접 변경 시도
- 대량 요청 시 서비스 영향 테스트

---

#### A07: Authentication Failures (명칭 변경)

**현재 상태**: 구현됨 (명칭만 변경)

**점검 포인트**:
- 약한 비밀번호 정책 (최소 8자)
- 로그인 시도 제한 없음
- 세션 고정 공격 방어

**취약점 시연 방안**:
- 무차별 대입 공격 시뮬레이션 (rate limit 없음)
- 약한 비밀번호 설정 가능 여부

---

#### A08: Software or Data Integrity Failures (유지)

**현재 상태**: 구현됨

**점검 포인트**:
- 배포 아티팩트 서명/검증 부재
- 시드 데이터 변경 추적
- 자동 업데이트 검증

**취약점 시연 방안**:
- Docker 이미지 무결성 검증 부재 확인
- 코드 변경 이력 추적 체계 점검

---

#### A09: Security Logging and Alerting Failures (명칭 변경)

**현재 상태**: 구현됨 (Monitoring → Alerting 강조)

**점검 포인트**:
- 핵심 이벤트 로깅 (로그인, 권한변경, 민원처리)
- 로그 무결성 보호
- **실시간 알림 체계** (신규 강조)
- 민감 정보 로깅 방지

**취약점 시연 방안**:
- AuditLog 테이블 조회
- 알림 시스템 부재 확인

**서비스 내 개선**:
```python
# 알림 시뮬레이션 기능 추가
# - 의심스러운 활동 감지 시 알림 트리거
# - 관리자 대시보드에 알림 표시
```

---

#### A10: Mishandling of Exceptional Conditions (신규)

**현재 상태**: 미구현 (SSRF 대체)

**점검 포인트**:
- 예외 발생 시 민감 정보 노출 (CWE-209)
- Fail Open 동작 (CWE-636)
- NULL/빈 값 처리 누락
- 리소스 고갈 시 동작

**취약점 시연 방안**:
1. **에러 메시지 정보 노출**
   - 존재하지 않는 리소스 접근 시 상세 에러 노출
   - 데이터베이스 연결 실패 시 스택트레이스 노출

2. **Fail Open 시나리오**
   - 인증 서비스 장애 시 접근 허용 여부
   - 입력 검증 실패 시 기본값 처리

3. **리소스 제한 부재**
   - 대용량 파일 업로드 시 메모리 고갈
   - 무한 루프 유발 가능한 입력

**서비스 내 구현**:
```python
# /security/exception-test 엔드포인트 추가 (관리자 전용)
# 다양한 예외 상황 시뮬레이션:
# - 의도적 에러 발생
# - 타임아웃 시뮬레이션
# - 리소스 제한 테스트
```

---

## 4. 구현 우선순위

### Phase 1: 데이터 구조 변경 (필수)
1. `security_catalog.py` 전체 재작성
2. 코드 변경: A02↔A05 순서 교환, A03/A10 신규 추가
3. `OWASP_SCENARIOS.md` 문서 업데이트

### Phase 2: 신규 기능 추가 (권장)
1. A03: 공급망 점검 시뮬레이션 페이지
2. A10: 예외 처리 테스트 페이지
3. A09: 알림 시뮬레이션 기능

### Phase 3: 취약점 시연 환경 (선택)
1. 의도적 취약점이 포함된 별도 브랜치 생성
2. 각 시나리오별 PoC(Proof of Concept) 스크립트
3. 취약점 수정 전/후 비교 문서

## 5. 테스트 계획

### 5.1 기능 테스트
- `/security/scenarios` 목록에 10개 항목 표시
- 각 상세 페이지 정상 렌더링
- 관리자 전용 접근 제어 유지

### 5.2 시나리오 테스트
| ID | 테스트 케이스 | 예상 결과 |
|----|---------------|-----------|
| A01 | 타인 민원 접근 시도 | 403 또는 리다이렉트 |
| A02 | 기본 계정 로그인 | 성공 (취약점) |
| A03 | pip-audit 실행 | 취약점 목록 출력 |
| A10 | 잘못된 ID로 조회 | 표준 에러 페이지 |

## 6. 일정 (예상)

| 단계 | 작업 내용 | 예상 소요 |
|------|-----------|-----------|
| Phase 1 | 데이터 구조 변경 | 1일 |
| Phase 2 | 신규 기능 추가 | 2일 |
| Phase 3 | 취약점 시연 환경 | 2일 |
| 테스트 | 전체 검증 | 1일 |

## 7. 참고 자료

- [OWASP Top 10:2025 공식 문서](https://owasp.org/Top10/2025/)
- [A03: Software Supply Chain Failures](https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/)
- [A10: Mishandling of Exceptional Conditions](https://owasp.org/Top10/2025/A10_2025-Mishandling_of_Exceptional_Conditions/)

---

## 부록: security_catalog.py 예시 구조

```python
OWASP_TOP10_SCENARIOS = [
    {
        "id": "a01",
        "code": "A01:2025",
        "title": "Broken Access Control",
        "summary": "...",
        "service_case": "...",
        "checkpoints": [...],
        "mitigations": [...],
    },
    {
        "id": "a02",
        "code": "A02:2025",
        "title": "Security Misconfiguration",
        # 기존 A05 내용
    },
    {
        "id": "a03",
        "code": "A03:2025",
        "title": "Software Supply Chain Failures",
        # 신규 작성
    },
    # ... A04~A10
]
```
