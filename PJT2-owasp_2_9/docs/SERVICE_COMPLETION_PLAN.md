# 서비스 완성 계획서 (웹페이지 우선, 실행형)

목표: 문서만 보고도 "바로 구현/검증/제출"이 가능한 상태를 만든다.

## 1. 완성 정의 (Definition of Complete)

- DOC-1: 모든 필수 페이지 렌더링 정상
- DOC-2: 필수 기능 동작 정상
- DOC-3: 권한 분리 정상
- DOC-4: P0 테스트 100% 통과
- DOC-5: 문서/코드 정합성 확인 완료

## 2. 완료 체크리스트

## 2.1 페이지 체크

- `/`
- `/register`, `/login`, `/profile`
- `/health-info`, `/health-centers`, `/health-programs/{id}`
- `/posts`, `/posts/new`, `/posts/{id}`
- `/notices`, `/notices/{id}`
- `/complaints`, `/complaints/new`, `/complaints/{id}`
- `/admin`, `/admin/users`, `/admin/posts`, `/admin/notices`, `/admin/complaints`
- `/security/scenarios`, `/security/scenarios/{id}`

합격 기준.
- 200 또는 의도된 redirect
- 템플릿 렌더링 오류 없음
- 네비게이션 경로 정상

## 2.2 기능 체크

- 회원가입/로그인/로그아웃
- 프로필 수정
- 게시물 CRUD(분류 포함)
- 공공 의료 정보 페이지(소식/지원사업/FAQ/지역센터)
- 공지 생성/공개전환
- 민원 접수/상태변경
- 사용자 role 변경
- 감사로그 표시
- OWASP Top 10:2025 시나리오 페이지 열람(관리자, A01~A10)

합격 기준.
- DB에 실제 반영
- 성공/실패 메시지 일관성 유지

## 2.3 권한 체크

- 비로그인: 보호 페이지 접근 차단
- 일반 사용자: 관리자 페이지 접근 차단
- 작성자/관리자 외 게시물 수정 삭제 차단
- 관리자 외 민원 상태 변경 차단

합격 기준.
- 우회 가능한 케이스 0건

## 3. 실행 순서

1. 환경 실행
- `docker compose up --build`

2. 초기 계정 확인
- `admin / admin1234` 로그인 확인

3. 최소 데이터 생성
- 일반 사용자 2명
- 게시물 2건, 공지 2건, 민원 2건

4. P0 테스트 수행
- `docs/TEST_CASES.md` P0 전부 실행

5. 결함 수정 및 재검증
- 결함 로그 작성 -> 수정 -> 재테스트

6. 제출 패키지 점검
- 코드 + 문서 최신화 확인

## 4. 릴리스 게이트

- Gate-1: P0 100%
- Gate-2: Critical 0건
- Gate-3: 문서 최신화
- Gate-4: 데모 시나리오 1회 리허설 완료

## 5. 제출 전 최종 점검

- `docs/FEATURE_MATRIX.md` 요구사항 누락 확인
- `docs/API_SPEC.md` 라우트 일치 확인
- `docs/TEST_CASES.md` 결과 기록 완료
- `README.md` 실행 가이드 최신화

## 6. 산출물 패키지

- 코드: `web/`, `was/`, `docker-compose.yml`
- 문서: `docs/*.md`, `README.md`

## 7. 실패 시 복구 전략

- 기동 실패: DB 컨테이너 로그 확인 -> 환경변수 검증
- 권한 오류: `routes.py` 권한 가드 재검증
- 화면 오류: 템플릿 경로/변수 이름 확인
- 데이터 오류: 초기 데이터 재생성 후 테스트 재실행
