# 공공 의료 민원 포털 (3-Tier)

실습/과제용 3티어 웹서비스입니다.

- Web Tier: Nginx (`/web`)
- WAS Tier: Flask (`/was`)
- DB Tier: MariaDB (`docker-compose.yml`)

## 1) 현재 구현 범위

- 회원가입, 로그인/로그아웃, 마이페이지
- 마이페이지 의료 마이데이터(동의 기반 목데이터 불러오기/조회)
- 공공 의료 정보 페이지(소식/지원사업/FAQ/지역센터)
- 게시물 CRUD(분류 기반 민원 커뮤니티)
- 공지사항 조회(사용자) + 등록/공개전환(관리자)
- 민원 접수/조회(사용자) + 상태처리(관리자)
- 관리자 페이지
  - 사용자 계정 관리
  - 게시물 관리
  - 공지사항 관리
  - 민원 관리
- 감사 로그 기록/조회(관리자 `로그 모니터링`)

## 2) 실행 방법

```bash
cd /Users/sangwoolee/PJT2
docker compose up --build
```

접속 URL: `http://localhost:8080`

기본 관리자 계정.
- id: `admin`
- pw: `admin1234`

데모 데이터 생성(선택).

```bash
cd /Users/sangwoolee/PJT2/was
flask --app manage.py seed-demo
```

## 3) 검증 순서 (권장)

1. `docs/TEST_CASES.md`의 사전 데이터 준비 절차 수행
2. P0 테스트 전부 실행
3. Critical 결함 0건 확인
4. P1 테스트 실행 후 결과 기록

자동 테스트 실행(선택).

```bash
cd /Users/sangwoolee/PJT2/was
pip install -r requirements-dev.txt
PYTHONPATH=/Users/sangwoolee/PJT2/was pytest -q
```

테스트 결과 문서 자동 생성.

```bash
/Users/sangwoolee/PJT2/scripts/generate_test_report.sh
```

## 4) 문서 인덱스

- 구현 마스터 플랜: `docs/IMPLEMENTATION_MASTER_PLAN.md`
- 서비스 완성 계획: `docs/SERVICE_COMPLETION_PLAN.md`
- 요구사항 추적 매트릭스: `docs/FEATURE_MATRIX.md`
- API 명세: `docs/API_SPEC.md`
- 테스트 케이스: `docs/TEST_CASES.md`
- 테스트 결과: `docs/TEST_RESULTS.md`
- DB 스키마/시드: `docs/DB_SCHEMA_AND_SEED.md`
- OWASP Top 10:2025 시나리오: `docs/OWASP_SCENARIOS.md`
- OWASP 2025 마이그레이션 계획: `docs/OWASP_2025_MIGRATION_PLAN.md`
- 정책상 제한 사항: `docs/UNSUPPORTED_AND_SECURITY_NOTE.md`

## 5) 제출 전 체크

- 필수 요구사항 100% 구현
- P0 테스트 100% 통과
- Critical 결함 0건
- 문서-코드 불일치 0건

## 6) 참고

- 본 프로젝트는 교육용입니다.
- 실제 개인정보를 저장하지 마세요.
- 외부 공개 환경 배포 전 보안 강화(MFA, 입력검증 강화, 비밀관리, 감사추적 강화)가 필요합니다.
