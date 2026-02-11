# [취약점 분석 보고서] OWASP Top 10:2025 - A05: Injection (Cross-Site Scripting)

## 1. 공격지점 (Attack Surface)
- **URL**: `http://localhost:8090/posts`
- **입력 필드**: 게시판 상단의 검색창 (`q` 파라미터)
- **설명**: 사용자가 검색창에 입력한 검색어(`q`)를 서버가 화면에 다시 출력할 때, 필터링 없이 그대로 브라우저에 렌더링하도록 설정되어 있어 자바스크립트 삽입이 가능함.

## 2. 공격방식 (Attack Method)
- **공격 기법**: Reflected Cross-Site Scripting (Reflected XSS)
- **공격 페이로드**: `<script>alert('XSS Vulnerability!')</script>`
- **작동 원리**:
    1. 공격자가 검색창에 악성 스크립트 코드를 입력함.
    2. 서버는 입력받은 스크립트 코드를 검색어 변수(`q`)에 담아 템플릿으로 전달함.
    3. 템플릿 엔진(Jinja2)의 자동 이스케이프가 비활성화(`|safe`)되어 있어, 스크립트 태그가 HTML 엔티티로 변환되지 않고 그대로 브라우저에 전송됨.
    4. 피해자의 브라우저에서 해당 스크립트가 실행됨.

## 3. 취약코드 (Vulnerable Code)
- **위치**: `was/app/templates/posts/list.html`
- **코드**:
  ```html
  <!-- |safe 필터를 사용하여 사용자 입력값 q를 필터링 없이 렌더링함 -->
  <div style="margin-top: 15px; margin-bottom: 5px; color: var(--text-dim);">
    검색어 <strong>'{{ q|safe }}'</strong>에 대한 결과입니다.
  </div>
  ```

## 4. 개선코드 (Mitigation Code)
- **개선 방식**: 템플릿 엔진의 자동 이스케이프(Auto-escaping) 기능 활용
- **코드**:
  ```html
  <!-- |safe 필터를 제거하여 Jinja2가 자동으로 HTML 이스케이프를 수행하게 함 -->
  <div style="margin-top: 15px; margin-bottom: 5px; color: var(--text-dim);">
    검색어 <strong>'{{ q }}'</strong>에 대한 결과입니다.
  </div>
  ```
- **설명**: `|safe` 필터를 제거하면 `<script>`는 `&lt;script&gt;`로 변환되어 브라우저에서 코드로 실행되지 않고 평문 텍스트로 안전하게 표시됨.
