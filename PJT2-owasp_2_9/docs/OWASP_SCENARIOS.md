# OWASP Top 10:2025 시나리오 매핑

목적: 실제 공격 코드 없이, 평가 가능한 A01~A10 점검 시나리오를 제공한다.

> **버전**: OWASP Top 10:2025 기준

## 1. 서비스 내 위치

- 관리자 페이지 메뉴: `OWASP 시나리오`
- 경로:
  - 목록: `/security/scenarios`
  - 상세: `/security/scenarios/{scenario_id}`

## 2. 매핑표

| 코드 | 항목 | 본 서비스 점검 관점 | 증적 |
|------|------|---------------------|------|
| A01:2025 | Broken Access Control | 관리자/일반 사용자 경계, 타인 리소스 차단 (IDOR) | `/admin`, `/complaints/{id}` 접근 제어 로그 |
| A02:2025 | Security Misconfiguration | 기본계정/디버그/오류노출 설정 | 환경 설정 점검 체크리스트 |
| A03:2025 | Software Supply Chain Failures | 의존성 버전 관리, 취약 패키지, SBOM | pip-audit 결과, requirements.txt |
| A04:2025 | Cryptographic Failures | 시크릿 관리, 해시 저장, 민감정보 노출 | 설정/로그 점검 결과 |
| A05:2025 | Injection | 검색/입력 파라미터 처리 안정성 | ORM 사용 및 입력 검증 코드 |
| A06:2025 | Insecure Design | 상태 전이/업무 규칙 누락, Rate limiting | 민원 처리 플로우 점검 |
| A07:2025 | Authentication Failures | 비밀번호/세션/로그인 정책 | 인증 테스트 결과 |
| A08:2025 | Software or Data Integrity Failures | 코드/설정/배포 무결성 관리 | 변경 이력/검증 절차 |
| A09:2025 | Security Logging and Alerting Failures | 감사 로그, 모니터링, 알림 체계 | `/admin` 감사 로그 테이블 |
| A10:2025 | Mishandling of Exceptional Conditions | 예외 처리, Fail Open/Closed, 에러 노출 | 에러 핸들링 테스트 결과 |

## 3. 2021 대비 주요 변경 사항

### 신규 항목
- **A03: Software Supply Chain Failures** - 기존 A06(Vulnerable Components) 확장
  - SolarWinds, Log4Shell 등 공급망 공격 급증 반영
  - SBOM, CI/CD 보안, 의존성 관리 포함

- **A10: Mishandling of Exceptional Conditions** - 기존 A10(SSRF) 대체
  - 예외 처리 실패, Fail Open, 에러 정보 노출
  - 24개 CWE 매핑

### 순위 변동
| 항목 | 2021 | 2025 |
|------|------|------|
| Security Misconfiguration | A05 | A02 |
| Cryptographic Failures | A02 | A04 |
| Injection | A03 | A05 |
| Insecure Design | A04 | A06 |

### 명칭 변경
- A07: Identification and Authentication Failures → **Authentication Failures**
- A09: Security Logging and Monitoring Failures → **Security Logging and Alerting Failures**

## 4. 평가 운영 방법

1. 관리자 계정으로 `/security/scenarios` 접속
2. A01~A10 상세 페이지의 체크포인트 수행
3. 증적(화면 캡처, 로그, 테스트 결과)을 수집
4. 개선 전/후 비교 내용을 보고서에 반영

### 점검 도구 권장
| 항목 | 도구 |
|------|------|
| A03 | `pip-audit`, `safety`, `trivy` |
| A05 | `sqlmap`, `burp suite` |
| A07 | `hydra`, `burp intruder` |

## 5. 안전 원칙

- 실서비스/공개망에서 공격 행위 재현 금지
- 실제 악용 가능한 취약 코드 삽입 금지
- 로컬 또는 폐쇄망 실습 환경에서만 검증 수행

## 6. 참고 자료

- [OWASP Top 10:2025 공식](https://owasp.org/Top10/2025/)
- [A03: Software Supply Chain Failures](https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/)
- [A10: Mishandling of Exceptional Conditions](https://owasp.org/Top10/2025/A10_2025-Mishandling_of_Exceptional_Conditions/)
