# API 명세서 (v2, 구현 기준)

대상 서비스: 공공 의료 민원 포털

## 1. 공통 규약

- Base URL: `/`
- 인증: 세션 쿠키 (`Flask-Login`)
- 요청 형식: `application/x-www-form-urlencoded` (HTML form)
- 응답 형식: HTML 렌더링 또는 Redirect (`302`)
- 시간대: KST 기준 표시

## 2. 입력 검증 규칙

### 게시물/공지/민원 정책 (권장)
- `username`: 3~50자, 공백 불가
- `email`: 이메일 형식
- `full_name`: 1~100자
- `phone`: 7~20자
- `password`: 8자 이상 권장

### 목표 정책 (권장)
- `title`: 1~200자
- `content`: 1자 이상
- `post.category`: `general|medical_service|insurance_billing|privacy_records|facility_access|vaccination|digital_service`
- `complaint.category`: `general|medical|privacy|billing|facility_access|vaccination|digital_service`
- `complaint.status`: `received|in_review|resolved|rejected`
- `role`: `user|admin`

### 현재 구현 수준 (v2 기준)
- 필수값 존재 여부 검증: 적용
- `username`/`email` 중복 검증: 적용
- enum 성격 값(`category`, `status`, `role`)은 UI/폼 기반으로 제한
- 길이 제한/정규식 기반 서버 검증은 차기 강화 항목

## 3. 에러/권한 정책

- 미인증 접근: 로그인 페이지로 이동
- 권한 부족: 이전 페이지 또는 메인 이동 + flash `danger`
- 없는 리소스 ID: `404`
- 검증 실패: 원래 폼으로 redirect + 오류 메시지

## 4. 엔드포인트 상세

## 4.1 인증/계정

### `GET /register`
- 권한: Public
- 목적: 회원가입 페이지 조회
- 성공: `200`, `auth/register.html`

### `POST /register`
- 권한: Public
- 목적: 회원가입 처리
- 요청 필드: `username`, `email`, `full_name`, `phone`, `password`
- 성공: `302 /login`, flash `success`
- 실패: `302 /register`, flash `danger`
- DB 영향: `user` 1건 생성

### `GET /login`
- 권한: Public
- 목적: 로그인 페이지 조회
- 성공: `200`, `auth/login.html`

### `POST /login`
- 권한: Public
- 목적: 로그인 처리
- 요청 필드: `username`, `password`
- 성공: `302 /`, 세션 생성, `audit_log` 기록
- 실패: `200 또는 302`, flash `danger`, `login_failed` 로그 기록

### `GET /logout`
- 권한: Authenticated
- 목적: 로그아웃
- 성공: `302 /`, 세션 삭제, `audit_log` 기록

### `GET /profile`
- 권한: Authenticated
- 목적: 내 정보 조회
- 성공: `200`, `auth/profile.html`

### `POST /profile`
- 권한: Authenticated
- 목적: 내 정보 수정
- 요청 필드: `full_name`, `phone`
- 성공: `302 /profile`, flash `success`
- DB 영향: `user` 갱신, `audit_log` 기록

### `POST /profile/mydata/fetch`
- 권한: Authenticated
- 목적: 의료 마이데이터(목데이터) 불러오기
- 요청 필드: `consent_mydata=on` (동의 체크)
- 성공: `302 /profile`, flash `success`
- 실패: `302 /profile`, flash `danger` (동의 누락)
- DB 영향: `my_data_snapshot` 생성, `audit_log` 기록(`mydata_fetch`)

## 4.2 게시판

### `GET /posts`
- 권한: Public
- 목적: 게시물 목록 조회
- 성공: `200`, `posts/list.html`
- Query: `q`, `category`, `page`

### `GET /posts/new`
- 권한: Authenticated
- 목적: 글 작성 페이지
- 성공: `200`, `posts/new.html`

### `POST /posts/new`
- 권한: Authenticated
- 목적: 글 작성
- 요청 필드: `title`, `content`, `category`, `attachments[]`(선택)
- 성공: `302 /posts`, flash `success`
- 실패: `302 /posts/new`, flash `danger`
- DB 영향: `post` 생성, `audit_log` 기록

### `GET /posts/{post_id}`
- 권한: Public
- 목적: 게시물 상세
- 성공: `200`, `posts/detail.html`
- 실패: `404`

### `POST /posts/{post_id}`
- 권한: 작성자 또는 관리자
- 목적: 게시물 수정
- 요청 필드: `title`, `content`, `category`, `attachments[]`(선택, 추가 업로드)
- 성공: `302 /posts/{post_id}`, flash `success`
- 실패: `302`, flash `danger`
- DB 영향: `post` 갱신, `audit_log` 기록

### `GET /posts/{post_id}/attachments/{attachment_id}`
- 권한: Public
- 목적: 게시물 첨부파일 다운로드
- 성공: `200` 파일 응답
- 실패: `404`

### `POST /posts/{post_id}/attachments/{attachment_id}/delete`
- 권한: 작성자 또는 관리자
- 목적: 게시물 첨부파일 삭제
- 성공: `302 /posts/{post_id}`, flash `info`
- 실패: `302`, flash `danger`

### `POST /posts/{post_id}/delete`
- 권한: 작성자 또는 관리자
- 목적: 게시물 삭제
- 성공: `302 /posts`, flash `info`
- 실패: `302`, flash `danger`
- DB 영향: `post` 삭제, `audit_log` 기록

## 4.3 공지사항

### `GET /notices`
- 권한: Public
- 목적: 공지 목록
- 동작: 일반 사용자 = 공개 공지만, 관리자 = 전체
- 성공: `200`, `notices/list.html`

### `GET /notices/{notice_id}`
- 권한: Public (비공개는 관리자만)
- 목적: 공지 상세
- 성공: `200`, `notices/detail.html`
- 실패: `302 /notices` 또는 `404`

## 4.4 민원

### `GET /complaints/guide`
- 권한: Public
- 목적: 민원 유형 가이드 및 SLA(처리기한) 안내
- 성공: `200`, `complaints/guide.html`

### `GET /complaints/faq`
- 권한: Public
- 목적: 민원 처리 단계/자주 묻는 질문 안내
- 성공: `200`, `complaints/faq.html`

### `GET /complaints`
- 권한: Authenticated
- 목적: 민원 목록
- 동작: 일반 사용자 = 본인만, 관리자 = 전체
- 성공: `200`, `complaints/list.html`

### `GET /complaints/new`
- 권한: Authenticated
- 목적: 민원 접수 페이지
- 성공: `200`, `complaints/new.html`

### `POST /complaints/new`
- 권한: Authenticated
- 목적: 민원 등록
- 요청 필드: `title`, `category`, `content`
- 성공: `302 /complaints`, flash `success`
- 실패: `302 /complaints/new`, flash `danger`
- DB 영향: `complaint` 생성, `audit_log` 기록

### `GET /complaints/{complaint_id}`
- 권한: 본인 또는 관리자
- 목적: 민원 상세
- 성공: `200`, `complaints/detail.html`
- 실패: `302 /complaints` 또는 `404`

### `POST /complaints/{complaint_id}`
- 권한: 관리자
- 목적: 민원 상태 변경
- 요청 필드: `status`
- 성공: `302 /complaints/{complaint_id}`, flash `success`
- 실패: `302`, flash `danger`
- DB 영향: `complaint.status`, `assigned_admin_id` 갱신, `audit_log` 기록

### `GET /complaints/{complaint_id}/report.pdf`
- 권한: 본인 또는 관리자
- 목적: 민원 결과 리포트 PDF 다운로드
- 성공: `200`, `application/pdf`
- 실패: `302 /complaints` 또는 `404`
- DB 영향: `audit_log` 기록(`complaint_report_download`)

## 4.5 관리자

### `GET /admin`
- 권한: Admin
- 목적: 통계/최근 로그 대시보드
- 성공: `200`, `admin/dashboard.html`

### `GET /admin/users`
- 권한: Admin
- 목적: 사용자 권한 관리 화면
- 성공: `200`, `admin/users.html`
- Query: `q`, `role`, `page`

### `POST /admin/users`
- 권한: Admin
- 목적: 사용자 role 변경
- 요청 필드: `user_id`, `role`
- 성공: `302 /admin/users`, flash `success`
- 실패: `302`, flash `danger`
- 보호 규칙: 본인 admin 권한 제거 금지

### `GET /admin/posts`
- 권한: Admin
- 목적: 게시물 관리 화면
- 성공: `200`, `admin/posts.html`
- Query: `q`, `category`, `page`

### `GET /admin/logs`
- 권한: Admin
- 목적: 로그인 이력/웹 요청 포함 감사 로그 조회
- 성공: `200`, `admin/logs.html`
- Query: `q`, `event`, `method`, `page`
- 비고:
  - `event=login|login_failed|logout|web_request|...`
  - `method=GET|POST|PUT|PATCH|DELETE` (주로 `web_request` 필터용)

## 4.6 공공 의료 정보

### `GET /health-info`
- 권한: Public
- 목적: 공공 의료 소식/지원사업/FAQ 통합 조회
- 성공: `200`, `health/info.html`

### `GET /health-centers`
- 권한: Public
- 목적: 지역 공공의료 연계센터 조회
- 성공: `200`, `health/centers.html`

### `GET /health-calendar`
- 권한: Public
- 목적: 예방접종/검진 일정 캘린더 조회
- 성공: `200`, `health/calendar.html`

### `GET /support-programs`
- 권한: Public
- 목적: 의료비 지원사업 안내 조회
- 성공: `200`, `health/support_programs.html`

### `GET /records/procedure`
- 권한: Public
- 목적: 의무기록/개인정보 열람·정정 절차 안내
- 성공: `200`, `health/records_procedure.html`

### `GET /health-programs/{program_id}`
- 권한: Public
- 목적: 지원사업 상세 안내
- 성공: `200`, `health/program_detail.html`
- 실패: `404`

### `GET /admin/notices`
- 권한: Admin
- 목적: 공지 관리 화면
- 성공: `200`, `admin/notices.html`
- Query: `q`, `visibility`, `page`

### `POST /admin/notices`
- 권한: Admin
- 목적: 공지 생성
- 요청 필드: `title`, `content`, `is_published`
- 성공: `302 /admin/notices`, flash `success`
- 실패: `302`, flash `danger`
- DB 영향: `notice` 생성, `audit_log` 기록

### `POST /admin/notices/{notice_id}/publish`
- 권한: Admin
- 목적: 공개/비공개 토글
- 성공: `302 /admin/notices`, flash `info`
- DB 영향: `notice.is_published` 토글, `audit_log` 기록

### `GET /admin/complaints`
- 권한: Admin
- 목적: 민원 관리 목록
- 성공: `200`, `admin/complaints.html`
- Query: `q`, `status`, `category`, `page`

### `GET /security/scenarios`
- 권한: Admin
- 목적: OWASP Top 10:2025 시나리오 목록
- 성공: `200`, `security/list.html`
- 항목: A01~A10 (2025 버전)

### `GET /security/scenarios/{scenario_id}`
- 권한: Admin
- 목적: OWASP Top 10:2025 항목별 상세 점검 페이지
- 성공: `200`, `security/detail.html`
- 실패: `404`
- 시나리오 ID: `a01`~`a10`

## 5. 라우트/템플릿 매핑

- `/` -> `index.html`
- `/register` -> `auth/register.html`
- `/login` -> `auth/login.html`
- `/profile` -> `auth/profile.html`
- `/posts*` -> `posts/*`
- `/health-info`, `/health-centers`, `/health-programs/*` -> `health/*`
- `/notices*` -> `notices/*`
- `/complaints*` -> `complaints/*`
- `/admin*` -> `admin/*`

## 6. 변경 관리 규칙

- 라우트 추가/삭제 시 이 문서와 `docs/FEATURE_MATRIX.md`를 동시 갱신한다.
- 검증 규칙 변경 시 `docs/TEST_CASES.md`의 관련 TC를 동기화한다.
