# 테스트 케이스 명세서 (v2)

목표: 신규 인원이 문서만 보고 동일한 결과를 재현할 수 있어야 한다.

## 1. 테스트 게이트

- Release Gate 1: P0 100% 통과
- Release Gate 2: Critical 0건
- Release Gate 3: P1 90% 이상 통과

## 2. 환경

- 실행: `docker compose up --build`
- URL: `http://localhost:8080`
- 관리자: `admin / admin1234`
- 일반 사용자: `user1`, `user2` (사전 생성)

## 3. 사전 데이터 준비

### 최소 준비 절차
1. 관리자 계정으로 로그인한다.
2. 일반 사용자 2개를 가입한다 (`user1`, `user2`).
3. `user1`로 게시물 2개를 작성한다.
4. 관리자 공지 2개를 만든다 (공개 1, 비공개 1).
5. `user1`로 민원 2개를 접수한다.

### 준비 완료 기준
- `/posts`에 게시물 2건 이상
- `/notices`에 공개 공지 1건 이상
- `/admin/notices`에 비공개 공지 1건 이상
- `/complaints`에 민원 2건 이상

## 4. 테스트 케이스 목록

## P0 인증/세션

### TC-AUTH-01 회원가입 성공
- Given: 비로그인 상태
- When: `/register`에 유효값 제출
- Then: `/login`으로 이동, 성공 메시지 표시

### TC-AUTH-02 로그인 성공
- Given: 등록된 계정 존재
- When: `/login`에 올바른 계정 입력
- Then: 메인 이동, 상단 네비에 `로그아웃` 노출

### TC-AUTH-03 로그인 실패
- Given: 등록된 계정 존재
- When: 잘못된 비밀번호 입력
- Then: 실패 메시지 표시, 로그인 유지 안 됨

### TC-AUTH-04 로그아웃
- Given: 로그인 상태
- When: `/logout` 접근
- Then: 비로그인 상태로 전환

## P0 권한

### TC-AUTHZ-01 미인증 접근 차단
- Given: 비로그인 상태
- When: `/profile` 접근
- Then: 로그인 페이지로 이동

### TC-AUTHZ-02 관리자 페이지 접근 차단
- Given: 일반 사용자 로그인
- When: `/admin` 접근
- Then: 접근 거부 메시지

### TC-AUTHZ-03 타인 게시물 수정 차단
- Given: `user1` 게시물 존재, `user2` 로그인
- When: `/posts/{user1_post_id}` POST 수정 시도
- Then: 수정 불가 메시지, 원문 유지

### TC-AUTHZ-04 타인 민원 조회 차단
- Given: `user1` 민원 존재, `user2` 로그인
- When: `/complaints/{user1_complaint_id}` 접근
- Then: 접근 거부

### TC-AUTHZ-05 비공개 공지 접근 차단
- Given: 비공개 공지 1건 존재, 일반 사용자 로그인
- When: `/notices/{private_notice_id}` 접근
- Then: 접근 거부 및 목록 이동

## P0 핵심 기능

### TC-PROF-01 프로필 수정
- Given: 로그인 상태
- When: `/profile`에서 이름/연락처 수정
- Then: 수정값 반영, 성공 메시지

### TC-PROF-02 의료 마이데이터 불러오기
- Given: 로그인 상태
- When: `/profile`에서 동의 체크 후 `내 의료데이터 불러오기` 실행
- Then: 마이페이지에 진료/복약/검진 목데이터가 렌더링된다

### TC-POST-01 게시물 생성
- Given: 로그인 상태
- When: `/posts/new` 작성
- Then: 목록에 새 게시물 표시

### TC-POST-02 게시물 수정(작성자)
- Given: 본인 게시물 존재
- When: `/posts/{id}` POST
- Then: 상세 페이지에 수정 반영

### TC-POST-03 게시물 삭제(작성자)
- Given: 본인 게시물 존재
- When: `/posts/{id}/delete` POST
- Then: 목록에서 사라짐

### TC-POST-04 게시물 상세 조회
- Given: 게시물 1건 이상 존재
- When: `/posts/{id}` GET
- Then: 제목/내용/작성자 노출

### TC-POST-05 게시물 수정(관리자)
- Given: 타인 게시물 존재, 관리자 로그인
- When: `/posts/{id}` POST
- Then: 수정 성공

### TC-POST-06 게시물 분류 필터
- Given: 서로 다른 분류의 게시물 존재
- When: `/posts?category=digital_service` 접근
- Then: 해당 분류 게시물만 목록에 표시

### TC-POST-07 게시물 첨부파일 업로드/다운로드
- Given: 로그인 상태
- When: `/posts/new`에서 파일 첨부 후 게시물 생성, 상세에서 다운로드 수행
- Then: 첨부파일이 저장되고 다운로드 응답이 정상 반환된다

### TC-NOTI-01 공지 사용자 목록
- Given: 공개/비공개 공지 존재
- When: 일반 사용자 `/notices`
- Then: 공개 공지만 보임

### TC-NOTI-02 관리자 공지 등록
- Given: 관리자 로그인
- When: `/admin/notices`에 새 공지 작성
- Then: 목록에 추가

### TC-NOTI-03 공지 상세 조회
- Given: 공개 공지 존재
- When: `/notices/{id}` 접근
- Then: 상세 내용 노출

### TC-NOTI-04 공지 공개 전환
- Given: 비공개 공지 존재
- When: `/admin/notices/{id}/publish` POST
- Then: 사용자 목록에 노출

### TC-COMP-01 민원 접수
- Given: 일반 사용자 로그인
- When: `/complaints/new` POST
- Then: 본인 목록에 표시

### TC-COMP-02 관리자 상태 변경
- Given: 민원 1건 존재, 관리자 로그인
- When: `/complaints/{id}` POST status 변경
- Then: 상태 업데이트, 담당 관리자 설정

### TC-COMP-03 일반 사용자 목록 범위
- Given: 사용자별 민원 존재
- When: `/complaints` 접근
- Then: 본인 민원만 보임

### TC-COMP-04 민원 가이드/FAQ 접근
- Given: 비로그인 또는 로그인 사용자
- When: `/complaints/guide`, `/complaints/faq` 접근
- Then: 민원 유형(SLA 포함)과 처리 단계 FAQ가 정상 렌더링된다

### TC-COMP-05 민원 결과 PDF 다운로드
- Given: 본인 민원 1건 이상 존재
- When: `/complaints/{id}/report.pdf` 접근
- Then: `application/pdf` 응답이 반환되고 파일 다운로드가 가능하다

## P1 운영/품질

### TC-ADMIN-01 관리자 대시보드
- Given: 관리자 로그인
- When: `/admin` 접근
- Then: 통계 카드/로그 테이블 보임

### TC-ADMIN-02 사용자 권한 변경
- Given: 관리자 로그인
- When: `/admin/users`에서 `user`->`admin` 변경
- Then: role 반영

### TC-ADMIN-03 게시물 관리 화면
- Given: 관리자 로그인
- When: `/admin/posts` 접근
- Then: 게시물 목록 정상 렌더링

### TC-ADMIN-04 민원 관리 화면
- Given: 관리자 로그인
- When: `/admin/complaints` 접근
- Then: 전체 민원 표시

### TC-ADMIN-05 사용자 관리 검색/필터
- Given: 관리자 로그인, 사용자 데이터 존재
- When: `/admin/users?q=user&role=user` 접근
- Then: 조건에 맞는 계정만 표시

### TC-ADMIN-06 게시물 관리 검색/페이지네이션
- Given: 관리자 로그인, 게시물 다수 존재
- When: `/admin/posts?q=진료&page=1` 접근
- Then: 검색 결과와 페이지 정보 표시

### TC-ADMIN-07 민원 관리 필터/페이지네이션
- Given: 관리자 로그인, 상태/카테고리별 민원 존재
- When: `/admin/complaints?status=received&category=general&page=1` 접근
- Then: 필터링된 민원 목록 표시

### TC-LOG-01 로그인 로그
- Given: 사용자가 로그인 수행
- When: 관리자 `/admin` 진입
- Then: 최근 로그에 `login` 존재

### TC-LOG-02 게시물 수정 로그
- Given: 게시물 수정 수행
- When: 관리자 `/admin` 진입
- Then: `post_update` 로그 존재

### TC-LOG-03 민원 상태 로그
- Given: 관리자 상태 변경 수행
- When: 관리자 `/admin` 진입
- Then: `complaint_status_update` 로그 존재

### TC-LOG-04 관리자 로그 조회/필터
- Given: 관리자 로그인, `login`/`web_request` 로그가 누적된 상태
- When: `/admin/logs?event=web_request&method=GET&q=/posts` 접근
- Then: 조건에 맞는 로그 목록이 표시되고, 일반 사용자는 접근 차단된다

### TC-ERR-01 404 처리
- Given: 임의 URL
- When: `/not-found-example` 접근
- Then: 404 응답

### TC-SEC-01 OWASP Top 10:2025 시나리오 목록 접근(관리자)
- Given: 관리자 로그인
- When: `/security/scenarios` 접근
- Then: A01:2025~A10:2025 목록 렌더링
- 확인 항목:
  - A01: Broken Access Control
  - A02: Security Misconfiguration
  - A03: Software Supply Chain Failures (신규)
  - A04: Cryptographic Failures
  - A05: Injection
  - A06: Insecure Design
  - A07: Authentication Failures
  - A08: Software or Data Integrity Failures
  - A09: Security Logging and Alerting Failures
  - A10: Mishandling of Exceptional Conditions (신규)

### TC-SEC-02 OWASP 시나리오 접근 차단(일반 사용자)
- Given: 일반 사용자 로그인
- When: `/security/scenarios` 접근
- Then: 접근 거부(redirect)

### TC-HEALTH-01 공공 의료 정보 페이지 접근
- Given: 비로그인 또는 로그인 사용자
- When: `/health-info`, `/health-centers` 접근
- Then: 공공 의료 정보 및 지역센터 페이지 정상 렌더링

### TC-HEALTH-02 지원사업 상세 접근
- Given: 비로그인 또는 로그인 사용자
- When: `/health-programs/vaccination` 접근
- Then: 상세 정보 노출, 존재하지 않는 ID는 404

### TC-HEALTH-03 공공의료 고도화 안내 페이지 접근
- Given: 비로그인 또는 로그인 사용자
- When: `/health-calendar`, `/support-programs`, `/records/procedure` 접근
- Then: 예방/검진 일정, 의료비 지원사업, 의무기록/개인정보 절차 페이지가 정상 렌더링된다

### TC-OPS-01 3티어 계층 기동
- Given: Docker 환경 정상
- When: `docker compose up --build` 실행
- Then: `web`, `was`, `db` 3개 서비스가 정상 기동

### TC-OPS-02 데이터 영속성
- Given: 게시물/민원 데이터 생성 후 컨테이너 재시작
- When: `docker compose restart` 실행
- Then: 기존 데이터 유지

### TC-DOC-01 문서 기반 온보딩
- Given: 신규 인원 1명
- When: `README.md` + `docs/*.md`만으로 실행 및 P0 테스트 수행
- Then: 별도 구두 설명 없이 기본 시나리오 재현 성공

## 5. 결함 분류

- Critical: 인증 실패, 권한 우회, 데이터 손실
- Major: 핵심 기능 실패, 잘못된 상태 저장
- Minor: UI/문구/정렬 이슈

## 6. 테스트 결과 기록 템플릿

- 실행 일시:
- 버전/커밋:
- 환경:
- 실행자:
- P0 통과율:
- P1 통과율:
- Critical 개수:
- 오픈 이슈 목록:
- 릴리스 승인 여부:
