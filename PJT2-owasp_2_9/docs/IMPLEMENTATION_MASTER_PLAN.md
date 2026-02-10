# 웹 서비스 구현 마스터 플랜 (v2)

문서 목적: "기획 -> 구현 -> 검증 -> 제출" 전 과정을 단일 문서로 통제한다.

## 1. 범위 확정

- 도메인: 공공 의료 민원 포털
- 아키텍처: 3티어 (`web`/`was`/`db`)
- 필수 기능:
  - 인증/계정
  - 게시판 CRUD(분류 기반)
  - 공공 의료 정보 페이지(소식/지원사업/지역센터/FAQ)
  - 공지사항(사용자 조회 + 관리자 관리)
  - 민원(사용자 접수 + 관리자 상태처리)
  - 관리자 페이지(사용자/게시물/공지/민원)
  - 감사로그

Out of Scope.
- 실서비스 배포
- 실제 공격 악용 코드 삽입
- 외부 연동 결제/문자 인증

## 2. 아키텍처 기준

- Web Tier: Nginx (Reverse Proxy)
- WAS Tier: Flask + SQLAlchemy
- DB Tier: MariaDB
- 실행 환경: Docker Compose

데이터 흐름.
1. Client -> Nginx (`:8080`)
2. Nginx -> Flask (`was:8000`)
3. Flask -> MariaDB (`db:3306`)

## 3. 구현 산출물 (필수)

- 코드
  - `docker-compose.yml`
  - `web/nginx.conf`
  - `was/app/models.py`
  - `was/app/routes.py`
  - `was/app/templates/*`
- 문서
  - `README.md`
  - `docs/FEATURE_MATRIX.md`
  - `docs/API_SPEC.md`
  - `docs/TEST_CASES.md`
  - `docs/OWASP_SCENARIOS.md` (OWASP Top 10:2025)
  - `docs/OWASP_2025_MIGRATION_PLAN.md`
  - `docs/TEST_RESULTS.md`
  - `docs/SERVICE_COMPLETION_PLAN.md`
  - `docs/DB_SCHEMA_AND_SEED.md`
  - `docs/UNSUPPORTED_AND_SECURITY_NOTE.md`

## 4. 단계별 실행 계획

## Phase 0. 기준선 고정

작업.
- 요구사항 ID 확정 (`FR-*`, `NFR-*`)
- 라우트/템플릿/모델 초기 매핑
- 테스트 ID 확정 (`TC-*`)

완료 기준.
- `docs/FEATURE_MATRIX.md`에 요구사항-코드-테스트 연결 완료

## Phase 1. 도메인 모델 구현

작업.
- 사용자/게시물/공지/민원/감사로그 모델 구현
- 관계(FK) 및 제약 확인

완료 기준.
- 마이그레이션 없이 `db.create_all()`로 테이블 생성
- 기본 관리자 계정 생성 가능

## Phase 2. 핵심 기능 구현

작업.
- 인증/세션
- 게시판 CRUD
- 공지 조회/관리
- 민원 접수/처리

완료 기준.
- P0 기능 시나리오 동작
- 권한 예외 처리 완료

## Phase 3. 관리자 기능 구현

작업.
- 대시보드 통계
- 사용자 role 관리
- 게시물/공지/민원 관리 화면
- 감사로그 표시

완료 기준.
- 관리자 전용 페이지 접근 제어 100%

## Phase 4. UI/UX 정리

작업.
- 네비게이션 연결
- 에러 메시지/성공 메시지 통일
- 모바일 해상도 최소 대응

완료 기준.
- 주요 페이지 링크 끊김 0건

## Phase 5. 검증 및 결함 수정

작업.
- `docs/TEST_CASES.md` 수행
- 결함 등록/수정/재검증

완료 기준.
- P0 100%, Critical 0건

## 5. 품질 게이트

- Gate A: 기능 게이트
  - 필수 라우트 누락 0개
- Gate B: 권한 게이트
  - 관리자/일반 사용자 경계 위반 0건
- Gate C: 테스트 게이트
  - P0 통과율 100%
- Gate D: 문서 게이트
  - 문서-코드 불일치 0건

## 6. 리스크 관리

| 리스크 | 영향 | 대응 |
|---|---|---|
| 권한 누락 | 보안/평가 감점 | 수정/삭제/관리 라우트 전수 점검 |
| 초기 데이터 부재 | 테스트 지연 | 시드 절차 문서화 + 최소 데이터 셋 |
| 문서-코드 불일치 | 구현 오류 | 변경 시 문서 동시 수정 룰 적용 |
| 데모 불안정 | 발표 실패 | 데모 계정/시나리오 사전 고정 |

## 7. 변경 관리 룰

- 라우트 변경: `docs/API_SPEC.md` 동시 수정
- 요구사항 변경: `docs/FEATURE_MATRIX.md` 동시 수정
- 동작 변경: `docs/TEST_CASES.md` 케이스 동시 수정

## 8. 최종 완료 선언 조건

아래 5개를 모두 충족해야 “완성”으로 판단.
1. 필수 요구사항 100% 구현
2. P0 테스트 100% 통과
3. Critical 결함 0건
4. 관리자 페이지 필수 기능 동작
5. 문서 최신 상태 유지
