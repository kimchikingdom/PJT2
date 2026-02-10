import re


USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ROLE_SET = {"user", "admin"}
COMPLAINT_CATEGORY_SET = {
    "general",
    "medical",
    "privacy",
    "billing",
    "facility_access",
    "vaccination",
    "digital_service",
}
COMPLAINT_STATUS_SET = {"received", "in_review", "resolved", "rejected"}
POST_CATEGORY_SET = {
    "general",
    "medical_service",
    "insurance_billing",
    "privacy_records",
    "facility_access",
    "vaccination",
    "digital_service",
}


def _required(value):
    return bool(value and str(value).strip())


def validate_registration(username, email, full_name, phone, password):
    errors = []
    if not all(
        _required(v)
        for v in [username, email, full_name, phone, password]
    ):
        errors.append("모든 필드를 입력해주세요.")

    username = (username or "").strip()
    email = (email or "").strip()
    full_name = (full_name or "").strip()
    phone = (phone or "").strip()
    password = password or ""

    if username and not USERNAME_RE.match(username):
        errors.append("아이디는 3~50자 영문/숫자/._-만 사용할 수 있습니다.")
    if email and not EMAIL_RE.match(email):
        errors.append("이메일 형식이 올바르지 않습니다.")
    if full_name and len(full_name) > 100:
        errors.append("이름은 100자 이하여야 합니다.")
    if phone and not (7 <= len(phone) <= 20):
        errors.append("연락처는 7~20자여야 합니다.")
    if password and len(password) < 8:
        errors.append("비밀번호는 8자 이상이어야 합니다.")
    return errors


def validate_profile(full_name, phone):
    errors = []
    full_name = (full_name or "").strip()
    phone = (phone or "").strip()
    if not full_name:
        errors.append("이름을 입력해주세요.")
    if not phone:
        errors.append("연락처를 입력해주세요.")
    if full_name and len(full_name) > 100:
        errors.append("이름은 100자 이하여야 합니다.")
    if phone and not (7 <= len(phone) <= 20):
        errors.append("연락처는 7~20자여야 합니다.")
    return errors


def validate_title_and_content(title, content):
    errors = []
    title = (title or "").strip()
    content = (content or "").strip()
    if not title:
        errors.append("제목을 입력해주세요.")
    if not content:
        errors.append("내용을 입력해주세요.")
    if title and len(title) > 200:
        errors.append("제목은 200자 이하여야 합니다.")
    return errors


def validate_role(role):
    if role not in ROLE_SET:
        return ["권한 값이 올바르지 않습니다."]
    return []


def validate_complaint_category(category):
    if category not in COMPLAINT_CATEGORY_SET:
        return ["민원 카테고리 값이 올바르지 않습니다."]
    return []


def validate_complaint_status(status):
    if status not in COMPLAINT_STATUS_SET:
        return ["민원 상태 값이 올바르지 않습니다."]
    return []


def validate_post_category(category):
    if category not in POST_CATEGORY_SET:
        return ["게시판 분류 값이 올바르지 않습니다."]
    return []
