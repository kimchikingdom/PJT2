# 요구사항 추적 매트릭스 (RTM)

문서 목적: 요구사항이 구현 코드와 테스트 케이스까지 연결되는지 추적한다.

## 평가 기준

- 요구사항 누락률 0%
- 필수 요구사항의 테스트 커버리지 100%
- Critical 결함 0건

## 매트릭스

| Req ID | 요구사항 | 우선순위 | 구현 라우트/화면 | 구현 파일 | 테스트 ID | 완료 기준 |
|---|---|---:|---|---|---|---|
| FR-001 | 회원가입 | P0 | `/register` | `was/app/routes.py`, `was/app/templates/auth/register.html` | TC-AUTH-01 | 중복/누락 검증 포함 성공 |
| FR-002 | 로그인/로그아웃 | P0 | `/login`, `/logout` | `was/app/routes.py`, `was/app/templates/auth/login.html` | TC-AUTH-02,03,04 | 세션 생성/삭제 정상 |
| FR-003 | 마이페이지/의료 마이데이터 | P0 | `/profile`, `/profile/mydata/fetch` | `was/app/routes.py`, `was/app/mydata_mock.py`, `was/app/templates/auth/profile.html` | TC-PROF-01,02 | 프로필 수정 + 동의 기반 마이데이터 조회 |
| FR-004 | 게시물 생성/조회(분류/첨부 포함) | P0 | `/posts`, `/posts/new`, `/posts/{id}` | `was/app/routes.py`, `was/app/templates/posts/*`, `was/app/models.py` | TC-POST-01,04,06,07 | 목록/상세에 즉시 반영, 분류/첨부 저장 |
| FR-005 | 게시물 수정/삭제 권한 | P0 | `/posts/{id}`, `/posts/{id}/delete` | `was/app/routes.py` | TC-POST-02,03,05 | 작성자/관리자만 허용 |
| FR-006 | 공지 사용자 조회 | P0 | `/notices`, `/notices/{id}` | `was/app/routes.py`, `was/app/templates/notices/*` | TC-NOTI-01,03 | 비공개 공지 차단 |
| FR-007 | 공지 관리자 관리 | P0 | `/admin/notices`, `/admin/notices/{id}/publish` | `was/app/routes.py`, `was/app/templates/admin/notices.html` | TC-NOTI-02,04 | 등록/공개전환 정상 |
| FR-008 | 민원 접수/조회 | P0 | `/complaints`, `/complaints/new`, `/complaints/{id}` | `was/app/routes.py`, `was/app/templates/complaints/*` | TC-COMP-01,03 | 본인 민원만 조회 |
| FR-009 | 민원 상태 처리 | P0 | `/complaints/{id}`(POST) | `was/app/routes.py` | TC-COMP-02 | 관리자만 상태 변경 |
| FR-010 | 관리자 대시보드 | P0 | `/admin` | `was/app/routes.py`, `was/app/templates/admin/dashboard.html` | TC-ADMIN-01 | 통계/로그 노출 |
| FR-011 | 사용자 계정 관리 | P0 | `/admin/users` | `was/app/routes.py`, `was/app/templates/admin/users.html` | TC-ADMIN-02 | role 변경 및 보호 규칙 |
| FR-012 | 게시물 관리 화면 | P1 | `/admin/posts` | `was/app/routes.py`, `was/app/templates/admin/posts.html` | TC-ADMIN-03 | 목록/상세 이동 가능 |
| FR-013 | 민원 관리 화면 | P1 | `/admin/complaints` | `was/app/routes.py`, `was/app/templates/admin/complaints.html` | TC-ADMIN-04 | 전체 민원 조회 가능 |
| FR-014 | 감사 로그 기록/조회 | P0 | 주요 액션 공통, `/admin/logs` | `was/app/routes.py`, `was/app/models.py`, `was/app/templates/admin/logs.html` | TC-LOG-01,02,03,04 | 로그인/요청/관리 액션 저장 및 관리자 검색 조회 |
| FR-015 | 관리자 검색/필터/페이지네이션 | P1 | `/admin/users`, `/admin/posts`, `/admin/notices`, `/admin/complaints` | `was/app/routes.py`, `was/app/templates/admin/*` | TC-ADMIN-05,06,07 | 검색조건 반영 및 페이지 이동 가능 |
| FR-016 | OWASP Top 10:2025 시나리오 페이지 | P1 | `/security/scenarios`, `/security/scenarios/{id}` | `was/app/routes.py`, `was/app/security_catalog.py`, `was/app/templates/security/*` | TC-SEC-01,02 | A01:2025~A10:2025 시나리오 열람 및 권한 통제 |
| FR-017 | 공공 의료 정보 포털 페이지 | P1 | `/health-info`, `/health-centers`, `/health-programs/{id}` | `was/app/routes.py`, `was/app/health_content.py`, `was/app/templates/health/*` | TC-HEALTH-01,02 | 정보/지원사업/센터 페이지 노출 |
| FR-018 | 공공의료 안내 고도화(가이드/캘린더/절차) | P1 | `/complaints/guide`, `/complaints/faq`, `/health-calendar`, `/support-programs`, `/records/procedure` | `was/app/routes.py`, `was/app/health_content.py`, `was/app/templates/complaints/*`, `was/app/templates/health/*` | TC-HEALTH-03, TC-COMP-04 | 민원 유형/SLA/일정/지원/개인정보 절차 안내 노출 |
| FR-019 | 민원 결과 PDF 리포트 다운로드 | P1 | `/complaints/{id}/report.pdf` | `was/app/routes.py`, `was/app/templates/complaints/detail.html`, `was/requirements.txt` | TC-COMP-05 | 본인/관리자 PDF 다운로드 가능 |
| NFR-001 | 3티어 구조 | P0 | web-was-db 분리 | `docker-compose.yml`, `web/nginx.conf` | TC-OPS-01 | 계층 분리 기동 |
| NFR-002 | 데이터 영속성 | P1 | MariaDB volume | `docker-compose.yml` | TC-OPS-02 | 컨테이너 재기동 후 데이터 유지 |
| NFR-003 | 기본 운영 문서 | P0 | 실행/테스트/완성계획 | `README.md`, `docs/*` | TC-DOC-01 | 신규 인원이 문서만으로 실행 가능 |

## 상태 정의

- `Not Started`: 구현 없음
- `In Progress`: 구현 중 (테스트 미완)
- `Done`: 구현 + 테스트 통과
- `Blocked`: 외부 이슈로 진행 불가

## 문서/코드 변경 규칙

- 라우트 변경 시 `docs/API_SPEC.md`와 이 문서를 같은 커밋에서 수정한다.
- 테스트 케이스 추가/수정 시 `docs/TEST_CASES.md` 테스트 ID를 동기화한다.
