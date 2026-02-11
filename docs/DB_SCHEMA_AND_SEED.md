# DB 스키마 및 시드 데이터 명세

대상 DB: MariaDB (`civic_portal`)

## 1. 테이블 정의

## 1.1 user

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | INT | PK, AUTO_INCREMENT | 사용자 식별자 |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 로그인 아이디 |
| email | VARCHAR(120) | UNIQUE, NOT NULL | 이메일 |
| full_name | VARCHAR(100) | NOT NULL | 이름 |
| phone | VARCHAR(20) | NOT NULL | 연락처 |
| password_hash | VARCHAR(255) | NOT NULL | 비밀번호 해시 |
| role | VARCHAR(20) | NOT NULL, default `user` | `user` 또는 `admin` |
| created_at | DATETIME | NOT NULL | 생성 시각 |

## 1.2 post

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | INT | PK, AUTO_INCREMENT | 게시물 ID |
| title | VARCHAR(200) | NOT NULL | 제목 |
| content | TEXT | NOT NULL | 내용 |
| category | VARCHAR(50) | NOT NULL, default `general` | 게시판 분류 |
| status | VARCHAR(20) | NOT NULL, default `open` | 게시 상태 |
| created_at | DATETIME | NOT NULL | 생성 시각 |
| updated_at | DATETIME | NULL | 수정 시각 |
| user_id | INT | FK -> user.id, NOT NULL | 작성자 |

## 1.2-1 post_attachment

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | INT | PK, AUTO_INCREMENT | 첨부파일 ID |
| post_id | INT | FK -> post.id, NOT NULL | 게시물 ID |
| original_name | VARCHAR(255) | NOT NULL | 원본 파일명 |
| stored_name | VARCHAR(255) | UNIQUE, NOT NULL | 저장 파일명 |
| mime_type | VARCHAR(120) | NULL | MIME 타입 |
| file_size | INT | NOT NULL, default `0` | 파일 크기(Byte) |
| created_at | DATETIME | NOT NULL | 업로드 시각 |

## 1.3 notice

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | INT | PK, AUTO_INCREMENT | 공지 ID |
| title | VARCHAR(200) | NOT NULL | 제목 |
| content | TEXT | NOT NULL | 내용 |
| is_published | BOOLEAN | NOT NULL, default false | 공개 여부 |
| created_at | DATETIME | NOT NULL | 생성 시각 |
| created_by | INT | FK -> user.id, NULL | 생성 관리자 |

## 1.4 complaint

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | INT | PK, AUTO_INCREMENT | 민원 ID |
| title | VARCHAR(200) | NOT NULL | 제목 |
| content | TEXT | NOT NULL | 내용 |
| category | VARCHAR(50) | NOT NULL | 민원 카테고리 |
| status | VARCHAR(30) | NOT NULL, default `received` | 처리 상태 |
| created_at | DATETIME | NOT NULL | 접수 시각 |
| updated_at | DATETIME | NULL | 갱신 시각 |
| user_id | INT | FK -> user.id, NOT NULL | 접수자 |
| assigned_admin_id | INT | FK -> user.id, NULL | 담당 관리자 |

## 1.5 audit_log

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | INT | PK, AUTO_INCREMENT | 로그 ID |
| actor_id | INT | FK -> user.id, NULL | 수행자 |
| action | VARCHAR(200) | NOT NULL | 액션명 |
| target_type | VARCHAR(50) | NULL | 대상 타입 |
| target_id | VARCHAR(50) | NULL | 대상 ID |
| meta | TEXT | NULL | 부가 정보 |
| created_at | DATETIME | NOT NULL | 기록 시각 |

## 1.6 my_data_snapshot

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | INT | PK, AUTO_INCREMENT | 스냅샷 ID |
| user_id | INT | FK -> user.id, NOT NULL | 소유 사용자 |
| source | VARCHAR(20) | NOT NULL, default `MOCK` | 데이터 출처 |
| consent_given | BOOLEAN | NOT NULL, default false | 동의 여부 |
| consent_at | DATETIME | NULL | 동의 시각 |
| payload_json | TEXT | NOT NULL | 목데이터 JSON |
| fetched_at | DATETIME | NOT NULL | 불러온 시각 |
| created_at | DATETIME | NOT NULL | 생성 시각 |

## 1.7 provider_subject (의료 마이데이터 제공기관 데이터)

외부 MyData 제공기관이 보유한 마스터 데이터(목데이터) 테이블입니다.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | INT | PK, AUTO_INCREMENT | 제공기관 Subject ID |
| subject_ref | VARCHAR(32) | UNIQUE, NOT NULL | 외부 식별자 (예: `SUBJ-0001`) |
| full_name | VARCHAR(100) | NOT NULL | 이름 |
| birth_date | DATE | NULL | 생년월일 |
| gender | VARCHAR(1) | NULL | `M`/`F` |
| resident_number | VARCHAR(20) | NULL | 주민번호(목데이터, 데모용) |
| phone | VARCHAR(30) | NULL | 연락처(목데이터) |
| payload_json | TEXT | NOT NULL | 의료 마이데이터 JSON |
| created_at | DATETIME | NOT NULL | 생성 시각 |
| updated_at | DATETIME | NULL | 갱신 시각 |

## 1.8 provider_consent (동의/연결)

포털 사용자와 제공기관 subject 데이터를 1:1로 연결하는 동의 레코드입니다.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | INT | PK, AUTO_INCREMENT | 동의 ID |
| user_id | INT | FK -> user.id, UNIQUE, NOT NULL | 포털 사용자 |
| provider_subject_id | INT | FK -> provider_subject.id, UNIQUE, NOT NULL | 제공기관 subject |
| status | VARCHAR(20) | NOT NULL, default `active` | `active`/`revoked` |
| consent_at | DATETIME | NOT NULL | 동의 시각 |
| revoked_at | DATETIME | NULL | 철회 시각 |
| created_at | DATETIME | NOT NULL | 생성 시각 |

## 1.9 provider_access_token (제공기관 토큰)

제공기관이 발급한 access token(목데이터) 저장용 테이블입니다.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | INT | PK, AUTO_INCREMENT | 토큰 ID |
| token | VARCHAR(128) | UNIQUE, NOT NULL | access token |
| client_id | VARCHAR(80) | NULL | 클라이언트 식별자 |
| consent_id | INT | FK -> provider_consent.id, NOT NULL | 동의 ID |
| issued_at | DATETIME | NOT NULL | 발급 시각 |
| expires_at | DATETIME | NOT NULL | 만료 시각 |
| revoked_at | DATETIME | NULL | 폐기 시각 |

## 2. 권장 인덱스

- `post(user_id, created_at)`
- `post_attachment(post_id, created_at)`
- `notice(is_published, created_at)`
- `complaint(user_id, status, created_at)`
- `audit_log(actor_id, created_at)`
- `my_data_snapshot(user_id, fetched_at)`
- `provider_subject(subject_ref)`
- `provider_consent(user_id)`
- `provider_access_token(token)`

## 3. 최소 시드 데이터

- 관리자 1명
  - username: `admin`
  - role: `admin`
- 일반 사용자 2명
  - `user1`, `user2`
- 게시물 2건 (`user1` 작성)
- 공지 2건 (공개 1, 비공개 1)
- 민원 2건 (`user1` 접수)
- 의료 마이데이터 스냅샷 1건 (`user1`)
- 제공기관 subject 100건 (`provider_subject`)

## 3.1 시드 명령

```bash
cd /Users/sangwoolee/PJT2/was
flask --app manage.py seed-demo
```

## 4. 시드 완료 확인 쿼리

```sql
SELECT COUNT(*) AS users FROM user;
SELECT COUNT(*) AS posts FROM post;
SELECT COUNT(*) AS post_attachments FROM post_attachment;
SELECT COUNT(*) AS notices FROM notice;
SELECT COUNT(*) AS complaints FROM complaint;
SELECT COUNT(*) AS logs FROM audit_log;
SELECT COUNT(*) AS mydata FROM my_data_snapshot;
SELECT COUNT(*) AS provider_subjects FROM provider_subject;
SELECT COUNT(*) AS provider_consents FROM provider_consent;
SELECT COUNT(*) AS provider_tokens FROM provider_access_token;
```

기준.
- users >= 3
- posts >= 2
- notices >= 2
- complaints >= 2
- mydata >= 1
- provider_subjects >= 100

## 5. 데이터 정합성 체크

- `complaint.assigned_admin_id`는 관리자 role 사용자만 가능
- 비공개 공지는 일반 사용자에게 노출되면 안 됨
- 삭제된 게시물은 목록에서 조회 불가
