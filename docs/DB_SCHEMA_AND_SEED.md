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

## 2. 권장 인덱스

- `post(user_id, created_at)`
- `post_attachment(post_id, created_at)`
- `notice(is_published, created_at)`
- `complaint(user_id, status, created_at)`
- `audit_log(actor_id, created_at)`
- `my_data_snapshot(user_id, fetched_at)`

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
```

기준.
- users >= 3
- posts >= 2
- notices >= 2
- complaints >= 2
- mydata >= 1

## 5. 데이터 정합성 체크

- `complaint.assigned_admin_id`는 관리자 role 사용자만 가능
- 비공개 공지는 일반 사용자에게 노출되면 안 됨
- 삭제된 게시물은 목록에서 조회 불가
