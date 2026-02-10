#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/sangwoolee/PJT2"
WAS_DIR="$ROOT/was"
REPORT="$ROOT/docs/TEST_RESULTS.md"
BASE_URL="http://localhost:8080"
VENV="/tmp/pjt2-venv"

if ! docker compose -f "$ROOT/docker-compose.yml" ps >/dev/null 2>&1; then
  echo "docker compose is not available" >&2
  exit 1
fi

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install -q -r "$WAS_DIR/requirements-dev.txt"

set +e
PYTEST_RAW=$(cd "$WAS_DIR" && PYTHONPATH="$WAS_DIR" pytest -q 2>&1)
PYTEST_EXIT=$?
set -e

HTTP_CODE() {
  curl -s -o /tmp/pjt2_report_body.$$ -w '%{http_code}' "$@"
}

ROOT_CODE=$(HTTP_CODE "$BASE_URL/")
POSTS_CODE=$(HTTP_CODE "$BASE_URL/posts")
HEALTH_INFO_CODE=$(HTTP_CODE "$BASE_URL/health-info")
HEALTH_CENTERS_CODE=$(HTTP_CODE "$BASE_URL/health-centers")
HEALTH_PROGRAM_CODE=$(HTTP_CODE "$BASE_URL/health-programs/vaccination")
HEALTH_CALENDAR_CODE=$(HTTP_CODE "$BASE_URL/health-calendar")
SUPPORT_PROGRAMS_CODE=$(HTTP_CODE "$BASE_URL/support-programs")
RECORDS_PROC_CODE=$(HTTP_CODE "$BASE_URL/records/procedure")
COMPLAINT_GUIDE_CODE=$(HTTP_CODE "$BASE_URL/complaints/guide")
COMPLAINT_FAQ_CODE=$(HTTP_CODE "$BASE_URL/complaints/faq")

rm -f /tmp/pjt2_user.cookies /tmp/pjt2_admin.cookies
USER_LOGIN_CODE=$(curl -s -c /tmp/pjt2_user.cookies -b /tmp/pjt2_user.cookies -o /tmp/pjt2_report_body.$$ -w '%{http_code}' \
  -X POST "$BASE_URL/login" -d 'username=user1&password=user12345')
USER_ADMIN_CODE=$(curl -s -b /tmp/pjt2_user.cookies -o /tmp/pjt2_report_body.$$ -w '%{http_code}' "$BASE_URL/admin")
USER_PRIVATE_NOTICE_CODE=$(curl -s -b /tmp/pjt2_user.cookies -o /tmp/pjt2_report_body.$$ -w '%{http_code}' "$BASE_URL/notices/2")
USER_COMPLAINT_PDF_CODE=$(curl -s -b /tmp/pjt2_user.cookies -o /tmp/pjt2_report_body.$$ -w '%{http_code}' "$BASE_URL/complaints/1/report.pdf")

ADMIN_LOGIN_CODE=$(curl -s -c /tmp/pjt2_admin.cookies -b /tmp/pjt2_admin.cookies -o /tmp/pjt2_report_body.$$ -w '%{http_code}' \
  -X POST "$BASE_URL/login" -d 'username=admin&password=admin1234')
ADMIN_ADMIN_CODE=$(curl -s -b /tmp/pjt2_admin.cookies -o /tmp/pjt2_report_body.$$ -w '%{http_code}' "$BASE_URL/admin")
ADMIN_LOGS_CODE=$(curl -s -b /tmp/pjt2_admin.cookies -o /tmp/pjt2_report_body.$$ -w '%{http_code}' "$BASE_URL/admin/logs")
ADMIN_PRIVATE_NOTICE_CODE=$(curl -s -b /tmp/pjt2_admin.cookies -o /tmp/pjt2_report_body.$$ -w '%{http_code}' "$BASE_URL/notices/2")
ADMIN_SCENARIO_CODE=$(curl -s -b /tmp/pjt2_admin.cookies -o /tmp/pjt2_report_body.$$ -w '%{http_code}' "$BASE_URL/security/scenarios")

SMOKE_PASS="PASS"
for expected_pair in \
  "ROOT_CODE:200" \
  "POSTS_CODE:200" \
  "HEALTH_INFO_CODE:200" \
  "HEALTH_CENTERS_CODE:200" \
  "HEALTH_PROGRAM_CODE:200" \
  "HEALTH_CALENDAR_CODE:200" \
  "SUPPORT_PROGRAMS_CODE:200" \
  "RECORDS_PROC_CODE:200" \
  "COMPLAINT_GUIDE_CODE:200" \
  "COMPLAINT_FAQ_CODE:200" \
  "USER_LOGIN_CODE:302" \
  "USER_ADMIN_CODE:302" \
  "USER_PRIVATE_NOTICE_CODE:302" \
  "USER_COMPLAINT_PDF_CODE:200" \
  "ADMIN_LOGIN_CODE:302" \
  "ADMIN_ADMIN_CODE:200" \
  "ADMIN_LOGS_CODE:200" \
  "ADMIN_PRIVATE_NOTICE_CODE:200" \
  "ADMIN_SCENARIO_CODE:200"; do
  key="${expected_pair%%:*}"
  expected="${expected_pair##*:}"
  actual="${!key}"
  if [ "$actual" != "$expected" ]; then
    SMOKE_PASS="FAIL"
    break
  fi
done

DB_COUNTS=$(docker compose -f "$ROOT/docker-compose.yml" exec -T db mariadb -uappuser -papppw civic_portal -N -e "\
SELECT CONCAT('users=', COUNT(*)) FROM user;\
SELECT CONCAT('posts=', COUNT(*)) FROM post;\
SELECT CONCAT('notices=', COUNT(*)) FROM notice;\
SELECT CONCAT('complaints=', COUNT(*)) FROM complaint;\
SELECT CONCAT('logs=', COUNT(*)) FROM audit_log;\
SELECT CONCAT('mydata=', COUNT(*)) FROM my_data_snapshot;\
" 2>/dev/null)

SERVICES=$(docker compose -f "$ROOT/docker-compose.yml" ps --format json)
RUN_AT=$(date '+%Y-%m-%d %H:%M:%S %Z')

cat > "$REPORT" <<MD
# TEST RESULTS

- Generated at: $RUN_AT
- Base URL: $BASE_URL

## 1. Service Status

\`docker compose ps --format json\`:

\`\`\`json
$SERVICES
\`\`\`

## 2. Automated Tests (pytest)

- Exit code: $PYTEST_EXIT

\`\`\`text
$PYTEST_RAW
\`\`\`

## 3. Smoke Checks

| Check | HTTP Code |
|---|---:|
| GET / | $ROOT_CODE |
| GET /posts | $POSTS_CODE |
| GET /health-info | $HEALTH_INFO_CODE |
| GET /health-centers | $HEALTH_CENTERS_CODE |
| GET /health-programs/vaccination | $HEALTH_PROGRAM_CODE |
| GET /health-calendar | $HEALTH_CALENDAR_CODE |
| GET /support-programs | $SUPPORT_PROGRAMS_CODE |
| GET /records/procedure | $RECORDS_PROC_CODE |
| GET /complaints/guide | $COMPLAINT_GUIDE_CODE |
| GET /complaints/faq | $COMPLAINT_FAQ_CODE |
| POST /login (user1) | $USER_LOGIN_CODE |
| GET /admin (user1) | $USER_ADMIN_CODE |
| GET /notices/2 private (user1) | $USER_PRIVATE_NOTICE_CODE |
| GET /complaints/1/report.pdf (user1) | $USER_COMPLAINT_PDF_CODE |
| POST /login (admin) | $ADMIN_LOGIN_CODE |
| GET /admin (admin) | $ADMIN_ADMIN_CODE |
| GET /admin/logs (admin) | $ADMIN_LOGS_CODE |
| GET /notices/2 private (admin) | $ADMIN_PRIVATE_NOTICE_CODE |
| GET /security/scenarios (admin) | $ADMIN_SCENARIO_CODE |

## 4. Seed Data Snapshot

\`\`\`text
$DB_COUNTS
\`\`\`

## 5. Result Summary

- pytest: $( [ "$PYTEST_EXIT" -eq 0 ] && echo "PASS" || echo "FAIL" )
- smoke critical checks: $SMOKE_PASS (status codes captured above)
MD

rm -f /tmp/pjt2_report_body.$$ /tmp/pjt2_user.cookies /tmp/pjt2_admin.cookies

echo "Generated: $REPORT"
