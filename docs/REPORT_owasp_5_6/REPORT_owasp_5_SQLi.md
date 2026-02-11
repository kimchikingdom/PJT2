# [취약점 분석 보고서] OWASP Top 10:2025 - A05: Injection

## 1. 공격지점 (Attack Surface)
- **URL**: `http://localhost:8090/login`
- **입력 필드**: 로그인 페이지의 사용자 아이디(`username`) 입력란
- **설명**: 로그인 시 입력받은 아이디 값을 서버 사이드에서 SQL 쿼리 문자열에 직접 결합하여 사용함에 따라 SQL 인젝션 공격이 가능함.

## 2. 공격방식 (Attack Method)
- **공격 기법**: SQL Injection (Auth Bypass)
- **공격 페이로드**: `' OR '1'='1' -- `
- **작동 원리**:
    1. 공격자가 아이디 필드에 `' OR '1'='1' -- `를 입력함.
    2. 서버 내부에서 생성되는 SQL은 `SELECT id FROM user WHERE username = '' OR '1'='1' -- '`이 됨.
    3. `WHERE` 절의 `'1'='1'` 조건이 항상 참(True)이 되며, 뒤의 주석(`-- `)에 의해 비밀번호 검증 쿼리 부분이 무시됨.
    4. 결과적으로 첫 번째 사용자(주로 관리자)의 계정으로 비밀번호 없이 로그인이 성공함.

## 3. 취약코드 (Vulnerable Code)
- **위치**: `was/app/routes.py`
- **코드**:
  ```python
  # 사용자 입력을 f-string을 통해 SQL 쿼리에 직접 삽입 (Vulnerable)
  sql = f"SELECT id FROM user WHERE username = '{username}'"
  result = db.session.execute(text(sql)).first()
  user = db.session.get(User, result[0]) if result else None
  
  # 인젝션 패턴 감지 시 비밀번호 검증 우회 로직 (시연용 취약점)
  is_sqli = "--" in username or "#" in username
  if user and (user.check_password(password) or is_sqli):
      # 로그인 성공 처리
  ```

## 4. 개선코드 (Mitigation Code)
- **개선 방식**: SQLAlchemy ORM 사용 또는 파라미터화된 쿼리(Parameterized Query) 사용
- **코드**:
  ```python
  # 1. ORM 사용 (추천)
  user = User.query.filter_by(username=username).first()
  
  # 2. 파라미터화된 쿼리 사용
  # sql = "SELECT id FROM user WHERE username = :username"
  # result = db.session.execute(text(sql), {"username": username}).first()
  
  # 안전한 비밀번호 검증
  if user and user.check_password(password):
      login_user(user)
  ```
