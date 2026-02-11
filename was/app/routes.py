import base64
import hashlib
import json
from io import BytesIO
import os
import pickle
import re
import subprocess
import time
import uuid
from datetime import UTC
from functools import wraps
from zoneinfo import ZoneInfo

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    Response,
    render_template,
    request,
    session,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
from sqlalchemy import func, or_, text
from werkzeug.utils import secure_filename

from app import db
from app.health_content import (
    COMPLAINT_STATUS_FAQ,
    COMPLAINT_TYPE_GUIDE,
    EMERGENCY_BANNER,
    HEALTH_FAQ,
    HEALTH_NEWS,
    HEALTH_PROGRAMS,
    MEDICAL_SUPPORT_PROGRAMS,
    RECORDS_PRIVACY_PROCEDURE,
    REGIONAL_CENTERS,
    VACCINATION_CHECKUP_CALENDAR,
)
from app.models import (
    AuditLog,
    Complaint,
    MyDataSnapshot,
    Notice,
    Post,
    PostAttachment,
    ProviderConsent,
    User,
    utc_now,
)
from app.provider_service import (
    fetch_provider_mydata_by_token,
    issue_provider_access_token,
    portal_fetch_mydata_via_provider_api,
    validate_provider_client,
)
from app.security_catalog import OWASP_TOP10_SCENARIOS
from app.validators import (
    COMPLAINT_CATEGORY_SET,
    COMPLAINT_STATUS_SET,
    POST_CATEGORY_SET,
    validate_complaint_category,
    validate_complaint_status,
    validate_post_category,
    validate_profile,
    validate_registration,
    validate_role,
    validate_title_and_content,
)

POST_CATEGORY_LABELS = {
    "general": "일반 문의",
    "medical_service": "진료 서비스",
    "insurance_billing": "보험/비용",
    "privacy_records": "개인정보/의무기록",
    "facility_access": "시설/접근성",
    "vaccination": "예방접종",
    "digital_service": "디지털 서비스",
}

COMPLAINT_CATEGORY_LABELS = {
    "general": "일반 행정",
    "medical": "진료 서비스",
    "billing": "보험/진료비",
    "privacy": "개인정보/의무기록",
    "facility_access": "시설/접근성",
    "vaccination": "예방접종",
    "digital_service": "디지털 서비스",
}

LOG_EVENT_OPTIONS = {
    "login_attempt",
    "login",
    "login_failed",
    "logout",
    "profile_update",
    "post_create",
    "post_update",
    "post_delete",
    "post_attachment_upload",
    "post_attachment_delete",
    "complaint_create",
    "complaint_status_update",
    "complaint_report_download",
    "notice_create",
    "notice_toggle_publish",
    "user_role_update",
    "web_request",
    "mydata_fetch",
    "mydata_report_download",
}

KST = ZoneInfo("Asia/Seoul")

_vulnlab_a06_request_log: dict = {}   # A06: {ip: [timestamp]}
_vulnlab_a07_attempt_log: dict = {}   # A07: {ip: int}
_global_login_attempts: dict = {"total": 0, "by_ip": {}}  # Track global login attempts for demo/bruteforce visualization

# ── 추가 시나리오 데모 데이터 ─────────────────────────────────────────────────
# 암호화2: MD5로 저장된 취약 비밀번호 데모 사용자 (실제 DB가 아닌 메모리 dict)
_DEMO_MD5_USERS = {
    "admin_demo":   hashlib.md5("admin1234".encode()).hexdigest(),   # 0192023a7bbd73250516f069df18b500
    "user1_demo":   hashlib.md5("user12345".encode()).hexdigest(),   # a9af47aba5d87a79bb9ce7dfc11e70f5
    "nurse_kim":    hashlib.md5("hospital99".encode()).hexdigest(),  # 5f4dcc3b5aa765d61d8327deb882cf99-ish
    "doctor_lee":   hashlib.md5("password1".encode()).hexdigest(),   # e38ad214943daad1d64c102faec29de4
    "patient_hong": hashlib.md5("hong1234".encode()).hexdigest(),
}

# 암호화3: 가짜 의료 파일 (IDOR 시연용)
_FAKE_PATIENT_FILES: dict = {
    "진료기록_홍길동_900101.pdf": (
        "[환자명] 홍길동  [생년월일] 1990-01-01  [주민번호] 900101-1234567\n"
        "[진단명] 고혈압 1기 (I10)\n[혈압] 140/90 mmHg\n"
        "[처방] 암로디핀 5mg 1일 1회 / 3개월분"
    ),
    "진료기록_김철수_850315.pdf": (
        "[환자명] 김철수  [생년월일] 1985-03-15  [주민번호] 850315-1987654\n"
        "[진단명] 제2형 당뇨병 (E11)\n[공복혈당] 180mg/dL\n"
        "[처방] 메트포르민 500mg 1일 2회 / 1개월분"
    ),
    "진료기록_이영희_920720.pdf": (
        "[환자명] 이영희  [생년월일] 1992-07-20  [주민번호] 920720-2345678\n"
        "[진단명] 요추 추간판 탈출증 L4-L5 (M51.1)\n"
        "[처방] 물리치료 주 2회 / 에토리콕시브 60mg 1일 1회"
    ),
    "민원결과_박민준_880503.pdf": (
        "[민원인] 박민준  [주민번호] 880503-1567890\n"
        "[민원유형] 의료비 과다 청구\n"
        "[처리결과] 환급 결정 (32,500원) — 담당: 이XX 주임"
    ),
}

# 인증2: 순차 세션 ID 취약점 데모
_weak_sessions: dict = {}       # {session_id(int): user_info_dict}
_weak_session_counter: list = [0]  # mutable int counter

POST_ATTACHMENT_ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "gif",
    "pdf",
    "txt",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "hwp",
    "hwpx",
}

PROFILE_IMAGE_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}


def admin_required(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        #if not current_user.is_authenticated or current_user.role != "admin":
        #    flash("관리자만 접근 가능합니다.", "danger")
        #    return redirect(url_for("index"))
        return func(*args, **kwargs)

    return wrapped


def log_action(action, target_type=None, target_id=None, meta=None, actor_id=None):
    entry = AuditLog(
        actor_id=(
            actor_id
            if actor_id is not None
            else (current_user.id if current_user.is_authenticated else None)
        ),
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        meta=meta,
    )
    try:
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()


def to_kst(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(KST)


def format_kst_datetime(dt, fmt="%Y-%m-%d %H:%M:%S"):
    converted = to_kst(dt)
    if converted is None:
        return "-"
    return converted.strftime(fmt)


def build_login_meta(username, result, client_ip, user_agent, reason=None):
    safe_username = (username or "-")[:50]
    safe_ua = (user_agent or "-")[:140]
    meta_parts = [
        "endpoint=/login",
        f"username={safe_username}",
        f"result={result}",
        f"ip={client_ip or '-'}",
        f"ua={safe_ua}",
    ]
    if reason:
        meta_parts.append(f"reason={reason}")
    return ";".join(meta_parts)


def flash_errors(errors):
    for message in errors:
        flash(message, "danger")


def parse_page(default=1):
    page = request.args.get("page", default, type=int)
    return page if page and page > 0 else default


def validate_attachment_files(file_storage_list):
    validated = []
    errors = []

    for file_storage in file_storage_list:
        original_name = (file_storage.filename or "").strip()
        if not original_name:
            continue

        safe_name = secure_filename(original_name)
        if not safe_name:
            errors.append("파일명 형식이 올바르지 않은 첨부파일이 있습니다.")
            continue
        if "." not in safe_name:
            errors.append(f"확장자가 없는 파일은 업로드할 수 없습니다: {original_name}")
            continue

        extension = safe_name.rsplit(".", 1)[1].lower()
        if extension not in POST_ATTACHMENT_ALLOWED_EXTENSIONS:
            errors.append(f"지원하지 않는 파일 형식입니다: {original_name}")
            continue

        validated.append((file_storage, safe_name, original_name))

    return validated, errors


def persist_post_attachments(post_id, validated_files):
    created = []
    for file_storage, safe_name, original_name in validated_files:
        stored_name = f"{uuid.uuid4().hex}_{safe_name}"
        upload_path = os.path.join(current_app.config["POST_UPLOAD_DIR"], stored_name)
        file_storage.save(upload_path)
        created.append(
            PostAttachment(
                post_id=post_id,
                original_name=original_name[:255],
                stored_name=stored_name,
                mime_type=file_storage.mimetype,
                file_size=os.path.getsize(upload_path) if os.path.exists(upload_path) else 0,
            )
        )
    return created


def remove_attachment_file(stored_name):
    file_path = os.path.join(current_app.config["POST_UPLOAD_DIR"], stored_name)
    if os.path.exists(file_path):
        os.remove(file_path)


def validate_profile_image_file(file_storage):
    if file_storage is None:
        return None, None
    original_name = (file_storage.filename or "").strip()
    if not original_name:
        return None, None
    safe_name = secure_filename(original_name)
    if not safe_name or "." not in safe_name:
        return None, "프로필 이미지 파일명이 올바르지 않습니다."
    extension = safe_name.rsplit(".", 1)[1].lower()
    if extension not in PROFILE_IMAGE_ALLOWED_EXTENSIONS:
        return None, "프로필 이미지는 jpg/jpeg/png/gif/webp 형식만 업로드할 수 있습니다."
    stored_name = f"profile_{uuid.uuid4().hex}.{extension}"
    return {
        "safe_name": safe_name,
        "stored_name": stored_name,
        "extension": extension,
    }, None


def remove_profile_image_file(stored_name):
    if not stored_name:
        return
    file_path = os.path.join(current_app.config["PROFILE_UPLOAD_DIR"], stored_name)
    if os.path.exists(file_path):
        os.remove(file_path)


def save_profile_image(file_storage, stored_name):
    upload_path = os.path.join(current_app.config["PROFILE_UPLOAD_DIR"], stored_name)
    file_storage.save(upload_path)


def build_complaint_report_pdf(complaint):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    font_name = "Helvetica"
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
        font_name = "HYSMyeongJo-Medium"
    except Exception:
        pass

    y = height - 48
    pdf.setFont(font_name, 16)
    pdf.drawString(40, y, "공공의료 민원 처리 결과 리포트")

    y -= 28
    pdf.setFont(font_name, 11)
    lines = [
        f"Complaint ID: {complaint.id}",
        f"Title: {complaint.title}",
        f"Category: {COMPLAINT_CATEGORY_LABELS.get(complaint.category, complaint.category)}",
        f"Status: {complaint.status}",
        f"Created At: {complaint.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Updated At: {complaint.updated_at.strftime('%Y-%m-%d %H:%M:%S') if complaint.updated_at else '-'}",
        f"Assigned Admin: {complaint.assigned_admin.username if complaint.assigned_admin else '-'}",
    ]
    for line in lines:
        pdf.drawString(40, y, line[:110])
        y -= 18

    y -= 6
    pdf.setFont(font_name, 12)
    pdf.drawString(40, y, "민원 내용")
    y -= 18

    pdf.setFont(font_name, 10)
    content_lines = (complaint.content or "").splitlines() or [""]
    for content_line in content_lines:
        chunk = content_line
        while chunk:
            part = chunk[:90]
            chunk = chunk[90:]
            if y < 48:
                pdf.showPage()
                y = height - 48
                pdf.setFont(font_name, 10)
            pdf.drawString(40, y, part)
            y -= 14

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.read()


def build_mydata_report_pdf(user, snapshot, payload):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    _, page_height = A4

    font_name = "Helvetica"
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
        font_name = "HYSMyeongJo-Medium"
    except Exception:
        pass

    y = page_height - 48

    def ensure_space(required_height=16):
        nonlocal y
        if y < 48 + required_height:
            pdf.showPage()
            y = page_height - 48
            pdf.setFont(font_name, 10)

    def draw_line(text, size=10, gap=14):
        nonlocal y
        ensure_space(gap)
        pdf.setFont(font_name, size)
        pdf.drawString(40, y, text[:110])
        y -= gap

    def draw_section_title(title):
        nonlocal y
        y -= 4
        draw_line(title, size=12, gap=18)

    pdf.setFont(font_name, 16)
    pdf.drawString(40, y, "의료 마이데이터 요약 리포트")
    y -= 26

    profile = payload.get("profile", {})
    cost = payload.get("costSummary", {})
    checkups = payload.get("checkups", {})
    visits = payload.get("visits", [])
    medications = payload.get("medications", [])
    vaccinations = payload.get("vaccinations", [])
    alerts = payload.get("alerts", [])

    draw_line(f"User: {user.username} ({user.full_name})", size=11, gap=16)
    draw_line(f"Snapshot ID: {snapshot.id}", size=11, gap=16)
    draw_line(f"Fetched At (KST): {format_kst_datetime(snapshot.fetched_at)}", size=11, gap=16)
    draw_line(f"Source: {snapshot.source}", size=11, gap=16)

    draw_section_title("기본 프로필")
    draw_line(f"생년월일: {profile.get('birthDate', '-')}")
    draw_line(f"성별: {profile.get('gender', '-')}")
    draw_line(f"혈액형: {profile.get('bloodType', '-')}")
    draw_line(f"알레르기: {profile.get('allergy', '-')}")

    draw_section_title("검진/비용 요약")
    draw_line(f"혈압: {checkups.get('bloodPressure', '-')}")
    draw_line(f"공복혈당: {checkups.get('fastingGlucose', '-')}")
    draw_line(f"HbA1c: {checkups.get('hba1c', '-')}")
    draw_line(f"총콜레스테롤: {checkups.get('totalCholesterol', '-')}")
    draw_line(f"본인부담금(연): {cost.get('outOfPocketTotal', 0):,}원")

    draw_section_title("최근 진료/복약/예방접종")
    draw_line(f"진료 건수: {len(visits)}")
    if visits:
        recent_visit = visits[0]
        draw_line(
            f"최근 진료: {recent_visit.get('date', '-')} / {recent_visit.get('provider', '-')} / {recent_visit.get('diagnosisName', '-')}"
        )
    draw_line(f"복약 건수: {len(medications)}")
    draw_line(f"예방접종 건수: {len(vaccinations)}")

    draw_section_title("건강 알림")
    if alerts:
        for alert in alerts[:6]:
            draw_line(f"- {alert}")
    else:
        draw_line("- 이상 징후 없음")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.read()


def init_routes(app):
    @app.template_filter("kst_datetime")
    def kst_datetime_filter(value, fmt="%Y-%m-%d %H:%M:%S"):
        return format_kst_datetime(value, fmt)

    @app.after_request
    def capture_web_request(response):
        endpoint = request.endpoint or ""
        if endpoint == "static" or request.path.startswith("/static/"):
            return response

        forwarded_for = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        client_ip = forwarded_for or request.remote_addr or "-"
        user_agent = request.user_agent.string if request.user_agent else "-"
        query_string = request.query_string.decode("utf-8", errors="ignore")
        meta = (
            f"status={response.status_code};endpoint={endpoint or '-'};"
            f"ip={client_ip};query={query_string[:120]};ua={user_agent[:140]}"
        )
        log_action(
            "web_request",
            target_type=request.method,
            target_id=(request.path or "-")[:50],
            meta=meta,
            actor_id=current_user.id if current_user.is_authenticated else None,
        )
        return response

    @app.context_processor
    def inject_global_banner():
        return {"emergency_banner": EMERGENCY_BANNER}

    @app.route("/")
    def index():
        latest_notices = Notice.query.filter_by(is_published=True).order_by(Notice.created_at.desc()).limit(5).all()
        latest_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
        highlighted_programs = HEALTH_PROGRAMS[:2]
        return render_template(
            "index.html",
            latest_notices=latest_notices,
            latest_posts=latest_posts,
            health_news=HEALTH_NEWS[:3],
            highlighted_programs=highlighted_programs,
            post_category_labels=POST_CATEGORY_LABELS,
            complaint_type_guide=COMPLAINT_TYPE_GUIDE[:3],
            schedule_preview=VACCINATION_CHECKUP_CALENDAR[:3],
            support_preview=MEDICAL_SUPPORT_PROGRAMS[:3],
        )

    @app.route("/health-info")
    def health_info():
        return render_template(
            "health/info.html",
            health_news=HEALTH_NEWS,
            health_programs=HEALTH_PROGRAMS,
            health_faq=HEALTH_FAQ,
        )

    @app.route("/health-centers")
    def health_centers():
        return render_template(
            "health/centers.html",
            centers=REGIONAL_CENTERS,
        )

    @app.route("/health-calendar")
    def health_calendar():
        return render_template(
            "health/calendar.html",
            schedules=VACCINATION_CHECKUP_CALENDAR,
        )

    @app.route("/support-programs")
    def support_programs():
        return render_template(
            "health/support_programs.html",
            programs=MEDICAL_SUPPORT_PROGRAMS,
        )

    @app.route("/records/procedure")
    def records_procedure():
        return render_template(
            "health/records_procedure.html",
            procedures=RECORDS_PRIVACY_PROCEDURE,
        )

    @app.route("/health-programs/<string:program_id>")
    def health_program_detail(program_id):
        program = next((item for item in HEALTH_PROGRAMS if item["id"] == program_id), None)
        if program is None:
            abort(404)
        return render_template(
            "health/program_detail.html",
            program=program,
        )

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            full_name = request.form.get("full_name", "").strip()
            phone = request.form.get("phone", "").strip()
            password = request.form.get("password", "")
            agree_required_terms = request.form.get("agree_required_terms") == "on"
            agree_optional_terms = request.form.get("agree_optional_terms") == "on"

            errors = validate_registration(username, email, full_name, phone, password)
            if not agree_required_terms:
                errors.append("필수 약관 동의가 필요합니다.")
            if errors:
                flash_errors(errors)
                return redirect(url_for("register"))

            if User.query.filter((User.username == username) | (User.email == email)).first():
                flash("이미 존재하는 사용자명 또는 이메일입니다.", "danger")
                return redirect(url_for("register"))

            user = User(
                username=username,
                email=email,
                full_name=full_name,
                phone=phone,
                required_terms_agreed=True,
                required_terms_agreed_at=utc_now(),
                optional_terms_agreed=agree_optional_terms,
                optional_terms_agreed_at=utc_now() if agree_optional_terms else None,
                role="user",
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("회원가입이 완료되었습니다. 로그인하세요.", "success")
            return redirect(url_for("login"))

        return render_template("auth/register.html")

    @app.route("/register/check-duplicate")
    def register_check_duplicate():
        field = request.args.get("field", "").strip().lower()
        value = request.args.get("value", "").strip()
        if field not in {"username", "email"}:
            return jsonify(
                {
                    "ok": False,
                    "available": False,
                    "message": "지원하지 않는 중복 확인 항목입니다.",
                }
            ), 400
        if not value:
            return jsonify(
                {
                    "ok": False,
                    "field": field,
                    "available": False,
                    "message": "확인할 값을 입력하세요.",
                }
            ), 400

        if field == "username":
            exists = User.query.filter_by(username=value).first() is not None
        else:
            exists = (
                User.query.filter(func.lower(User.email) == value.lower()).first() is not None
            )

        return jsonify(
            {
                "ok": True,
                "field": field,
                "value": value,
                "available": not exists,
                "message": (
                    "사용 가능한 값입니다."
                    if not exists
                    else "이미 사용 중인 값입니다."
                ),
            }
        )

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or "-"
            user_agent = request.user_agent.string if request.user_agent else "-"

            # Increment global/IP attempt counters
            _global_login_attempts["total"] += 1
            _global_login_attempts["by_ip"][client_ip] = _global_login_attempts["by_ip"].get(client_ip, 0) + 1

            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                session.pop("login_fail_count", None)
                session.pop("login_last_failed_username", None)
                login_meta = build_login_meta(user.username, "success", client_ip, user_agent)
                log_action(
                    "login_attempt",
                    target_type=request.method,
                    target_id=user.username[:50],
                    meta=login_meta,
                    actor_id=user.id,
                )
                login_user(user)
                log_action(
                    "login",
                    target_type=request.method,
                    target_id=user.username[:50],
                    meta=login_meta,
                    actor_id=user.id,
                )
                flash("로그인 성공", "success")
                return redirect(url_for("index"))

            if not username:
                fail_reason = "empty_username"
            elif user is None:
                fail_reason = "user_not_found"
            else:
                fail_reason = "invalid_password"
            attempted_id = username[:50] if username else "-"
            login_meta = build_login_meta(username, "failed", client_ip, user_agent, reason=fail_reason)
            log_action(
                "login_attempt",
                target_type=request.method,
                target_id=attempted_id,
                meta=login_meta,
                actor_id=None,
            )
            log_action(
                "login_failed",
                target_type=request.method,
                target_id=attempted_id,
                meta=login_meta,
                actor_id=None,
            )
            fail_count = int(session.get("login_fail_count", 0) or 0) + 1
            session["login_fail_count"] = fail_count
            session["login_last_failed_username"] = attempted_id
            flash("아이디 또는 비밀번호가 잘못되었습니다.", "danger")

        fail_count = int(session.get("login_fail_count", 0) or 0)
        return render_template(
            "auth/login.html",
            login_fail_count=fail_count,
            login_last_failed_username=session.get("login_last_failed_username"),
            total_login_attempts=_global_login_attempts["total"]
        )

    @app.route("/api/login-attempts")
    def get_login_attempts():
        return jsonify({
            "total": _global_login_attempts["total"],
            "by_ip": _global_login_attempts["by_ip"].get(request.remote_addr, 0)
        })

    @app.route("/logout")
    @login_required
    def logout():
        log_action("logout", "user", current_user.id)
        logout_user()
        flash("로그아웃 되었습니다.", "info")
        return redirect(url_for("index"))

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        if request.method == "POST":
            full_name = request.form.get("full_name", current_user.full_name).strip()
            phone = request.form.get("phone", current_user.phone).strip()
            email = request.form.get("email", current_user.email).strip()
            optional_terms_agreed = request.form.get("agree_optional_terms") == "on"
            remove_profile_image = request.form.get("remove_profile_image") == "on"
            current_password = request.form.get("current_password", "")
            profile_image_file = request.files.get("profile_image")
            image_meta, image_error = validate_profile_image_file(profile_image_file)

            errors = validate_profile(full_name, phone, email=email)
            if image_error:
                errors.append(image_error)
            if not current_password:
                errors.append("정보 수정을 위해 현재 비밀번호를 입력해주세요.")
            elif not current_user.check_password(current_password):
                errors.append("현재 비밀번호가 올바르지 않습니다.")
            existing_email = (
                User.query.filter(func.lower(User.email) == email.lower(), User.id != current_user.id).first()
                if email
                else None
            )
            if existing_email:
                errors.append("이미 사용 중인 이메일입니다.")
            if errors:
                flash_errors(errors)
                return redirect(url_for("profile"))

            previous_terms = current_user.optional_terms_agreed
            old_profile_image_name = current_user.profile_image_name
            if image_meta:
                try:
                    save_profile_image(profile_image_file, image_meta["stored_name"])
                except OSError:
                    flash("프로필 이미지 저장 중 오류가 발생했습니다.", "danger")
                    return redirect(url_for("profile"))
            current_user.full_name = full_name
            current_user.phone = phone
            current_user.email = email
            current_user.optional_terms_agreed = optional_terms_agreed
            current_user.optional_terms_agreed_at = utc_now() if optional_terms_agreed else None
            if remove_profile_image:
                current_user.profile_image_name = None
            if image_meta:
                current_user.profile_image_name = image_meta["stored_name"]

            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                if image_meta:
                    remove_profile_image_file(image_meta["stored_name"])
                flash("프로필 저장 중 오류가 발생했습니다.", "danger")
                return redirect(url_for("profile"))

            if remove_profile_image and old_profile_image_name:
                remove_profile_image_file(old_profile_image_name)
            if image_meta:
                if old_profile_image_name and old_profile_image_name != image_meta["stored_name"]:
                    remove_profile_image_file(old_profile_image_name)

            terms_changed = "yes" if previous_terms != optional_terms_agreed else "no"
            image_changed = "yes" if (remove_profile_image or image_meta) else "no"
            log_action(
                "profile_update",
                "user",
                current_user.id,
                meta=f"terms_changed={terms_changed};image_changed={image_changed}",
            )
            flash("프로필이 수정되었습니다.", "success")
            return redirect(url_for("profile"))

        snapshot = (
            MyDataSnapshot.query.filter_by(user_id=current_user.id)
            .order_by(MyDataSnapshot.fetched_at.desc(), MyDataSnapshot.id.desc())
            .first()
        )
        mydata = None
        if snapshot:
            try:
                mydata = json.loads(snapshot.payload_json)
            except json.JSONDecodeError:
                mydata = None
        my_posts = (
            Post.query.filter_by(user_id=current_user.id)
            .order_by(Post.created_at.desc())
            .limit(10)
            .all()
        )
        my_complaints = (
            Complaint.query.filter_by(user_id=current_user.id)
            .order_by(Complaint.created_at.desc())
            .limit(10)
            .all()
        )
        return render_template(
            "auth/profile.html",
            mydata_snapshot=snapshot,
            mydata=mydata,
            my_posts=my_posts,
            my_complaints=my_complaints,
            complaint_category_labels=COMPLAINT_CATEGORY_LABELS,
            post_category_labels=POST_CATEGORY_LABELS,
        )

    # ── Mock MyData Provider API ────────────────────────────────────────────────

    @app.route("/provider/oauth/token", methods=["POST"])
    def provider_oauth_token():
        data = request.get_json(silent=True) or {}
        client_id = (data.get("client_id") or request.form.get("client_id") or "").strip()
        client_secret = (data.get("client_secret") or request.form.get("client_secret") or "").strip()
        grant_type = (data.get("grant_type") or request.form.get("grant_type") or "consent").strip()
        consent_raw = data.get("consent_id") or request.form.get("consent_id")
        try:
            consent_id = int(consent_raw) if consent_raw is not None else None
        except (TypeError, ValueError):
            consent_id = None

        if not validate_provider_client(
            client_id,
            client_secret,
            expected_id=current_app.config.get("PROVIDER_CLIENT_ID", "portal-client"),
            expected_secret=current_app.config.get("PROVIDER_CLIENT_SECRET", "portal-secret"),
        ):
            return jsonify({"error": "invalid_client"}), 401

        if grant_type != "consent":
            return jsonify({"error": "unsupported_grant_type"}), 400
        if consent_id is None:
            return jsonify({"error": "invalid_request", "error_description": "consent_id is required"}), 400

        consent = db.session.get(ProviderConsent, consent_id)
        if consent is None or consent.status != "active":
            return jsonify({"error": "invalid_consent"}), 404

        ttl_seconds = int(current_app.config.get("PROVIDER_TOKEN_TTL_SECONDS", 600))
        token = issue_provider_access_token(consent, client_id=client_id, ttl_seconds=ttl_seconds)
        return jsonify(
            {
                "access_token": token.token,
                "token_type": "Bearer",
                "expires_in": ttl_seconds,
                "consent_id": consent.id,
            }
        )

    @app.route("/provider/api/v1/mydata", methods=["GET"])
    def provider_api_mydata():
        authz = request.headers.get("Authorization", "")
        token_str = ""
        if authz.lower().startswith("bearer "):
            token_str = authz.split(" ", 1)[1].strip()
        payload = fetch_provider_mydata_by_token(token_str)
        if payload is None:
            return jsonify({"error": "invalid_token"}), 401
        return jsonify(payload)

    @app.route("/profile/mydata/fetch", methods=["POST"])
    @login_required
    def profile_mydata_fetch():
        consent_given = request.form.get("consent_mydata") == "on"
        if not consent_given:
            flash("의료 마이데이터 불러오기 전에 수집/이용 동의가 필요합니다.", "danger")
            return redirect(url_for("profile"))

        payload, provider_consent, provider_token = portal_fetch_mydata_via_provider_api(
            current_user,
            client_id=current_app.config.get("PROVIDER_CLIENT_ID", "portal-client"),
            ttl_seconds=current_app.config.get("PROVIDER_TOKEN_TTL_SECONDS", 600),
            seed_subjects=current_app.config.get("PROVIDER_SEED_SUBJECTS", 100),
        )
        snapshot = MyDataSnapshot(
            user_id=current_user.id,
            source="PROVIDER_API",
            consent_given=True,
            consent_at=utc_now(),
            payload_json=json.dumps(payload, ensure_ascii=False),
            fetched_at=utc_now(),
        )
        db.session.add(snapshot)
        db.session.commit()
        log_action(
            "mydata_fetch",
            "mydata",
            snapshot.id,
            meta=(
                "source=PROVIDER_API;"
                f"consent_id={provider_consent.id};"
                f"token_id={provider_token.id};"
                f"subject_ref={payload.get('providerSubjectRef', '-')}"
            ),
        )
        flash("의료 마이데이터를 불러왔습니다. (제공기관 API 목데이터)", "success")
        return redirect(url_for("profile"))

    @app.route("/profile/mydata/report.pdf")
    @login_required
    def profile_mydata_report_pdf():
        snapshot = (
            MyDataSnapshot.query.filter_by(user_id=current_user.id)
            .order_by(MyDataSnapshot.fetched_at.desc(), MyDataSnapshot.id.desc())
            .first()
        )
        if snapshot is None:
            flash("다운로드 가능한 의료 마이데이터가 없습니다.", "danger")
            return redirect(url_for("profile"))

        try:
            payload = json.loads(snapshot.payload_json)
        except json.JSONDecodeError:
            flash("마이데이터 형식이 올바르지 않아 리포트를 생성할 수 없습니다.", "danger")
            return redirect(url_for("profile"))

        pdf_bytes = build_mydata_report_pdf(current_user, snapshot, payload)
        log_action("mydata_report_download", "mydata", snapshot.id, meta=f"source={snapshot.source}")
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=mydata_{current_user.username}_{snapshot.id}.pdf"
                )
            },
        )

    @app.route("/posts")
    def posts_list():
        q = request.args.get("q", "").strip()
        category = request.args.get("category", "all")
        query = Post.query.join(User, Post.user_id == User.id)

        if q:
            keyword = f"%{q}%"
            query = query.filter(
                (Post.title.ilike(keyword))
                | (Post.content.ilike(keyword))
                | (User.username.ilike(keyword))
            )

        if category in POST_CATEGORY_SET:
            query = query.filter(Post.category == category)
        else:
            category = "all"

        pagination = query.order_by(Post.created_at.desc()).paginate(
            page=parse_page(),
            per_page=10,
            error_out=False,
        )
        return render_template(
            "posts/list.html",
            posts=pagination.items,
            pagination=pagination,
            q=q,
            category=category,
            category_options=sorted(POST_CATEGORY_SET),
            post_category_labels=POST_CATEGORY_LABELS,
        )

    @app.route("/posts/new", methods=["GET", "POST"])
    @login_required
    def posts_new():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            category = request.form.get("category", "general").strip()
            validated_files, file_errors = validate_attachment_files(
                request.files.getlist("attachments")
            )
            errors = validate_title_and_content(title, content)
            errors.extend(validate_post_category(category))
            errors.extend(file_errors)
            if errors:
                flash_errors(errors)
                return redirect(url_for("posts_new"))

            post = Post(
                title=title,
                content=content,
                category=category,
                user_id=current_user.id,
            )
            db.session.add(post)
            db.session.flush()
            attachment_entities = persist_post_attachments(post.id, validated_files)
            for entity in attachment_entities:
                db.session.add(entity)
            db.session.commit()
            log_action("post_create", "post", post.id)
            if attachment_entities:
                log_action(
                    "post_attachment_upload",
                    "post",
                    post.id,
                    meta=f"count={len(attachment_entities)}",
                )
            flash("게시물이 등록되었습니다.", "success")
            return redirect(url_for("posts_list"))
        return render_template(
            "posts/new.html",
            category_options=sorted(POST_CATEGORY_SET),
            post_category_labels=POST_CATEGORY_LABELS,
        )

    @app.route("/posts/<int:post_id>", methods=["GET", "POST"])
    def posts_detail(post_id):
        post = db.get_or_404(Post, post_id)

        if request.method == "POST":
            if not current_user.is_authenticated:
                flash("로그인이 필요합니다.", "danger")
                return redirect(url_for("login"))
            if current_user.id != post.user_id and current_user.role != "admin":
                flash("수정 권한이 없습니다.", "danger")
                return redirect(url_for("posts_detail", post_id=post_id))

            title = request.form.get("title", post.title).strip()
            content = request.form.get("content", post.content).strip()
            category = request.form.get("category", post.category).strip()
            validated_files, file_errors = validate_attachment_files(
                request.files.getlist("attachments")
            )
            errors = validate_title_and_content(title, content)
            errors.extend(validate_post_category(category))
            errors.extend(file_errors)
            if errors:
                flash_errors(errors)
                return redirect(url_for("posts_detail", post_id=post_id))

            post.title = title
            post.content = content
            post.category = category
            attachment_entities = persist_post_attachments(post.id, validated_files)
            for entity in attachment_entities:
                db.session.add(entity)
            db.session.commit()
            log_action("post_update", "post", post.id)
            if attachment_entities:
                log_action(
                    "post_attachment_upload",
                    "post",
                    post.id,
                    meta=f"count={len(attachment_entities)}",
                )
            flash("게시물이 수정되었습니다.", "success")
            return redirect(url_for("posts_detail", post_id=post.id))

        return render_template(
            "posts/detail.html",
            post=post,
            category_options=sorted(POST_CATEGORY_SET),
            post_category_labels=POST_CATEGORY_LABELS,
        )

    @app.route("/posts/<int:post_id>/delete", methods=["POST"])
    @login_required
    def posts_delete(post_id):
        post = db.get_or_404(Post, post_id)
        if current_user.id != post.user_id and current_user.role != "admin":
            flash("삭제 권한이 없습니다.", "danger")
            return redirect(url_for("posts_detail", post_id=post_id))

        for attachment in post.attachments:
            remove_attachment_file(attachment.stored_name)
        db.session.delete(post)
        db.session.commit()
        log_action("post_delete", "post", post_id)
        flash("게시물이 삭제되었습니다.", "info")
        return redirect(url_for("posts_list"))

    @app.route("/posts/<int:post_id>/attachments/<int:attachment_id>")
    def post_attachment_download(post_id, attachment_id):
        attachment = PostAttachment.query.filter_by(
            id=attachment_id,
            post_id=post_id,
        ).first_or_404()
        return send_from_directory(
            current_app.config["POST_UPLOAD_DIR"],
            attachment.stored_name,
            as_attachment=True,
            download_name=attachment.original_name,
        )

    @app.route("/posts/<int:post_id>/attachments/<int:attachment_id>/delete", methods=["POST"])
    @login_required
    def post_attachment_delete(post_id, attachment_id):
        attachment = PostAttachment.query.filter_by(
            id=attachment_id,
            post_id=post_id,
        ).first_or_404()
        post = attachment.post
        if current_user.id != post.user_id and current_user.role != "admin":
            flash("첨부파일 삭제 권한이 없습니다.", "danger")
            return redirect(url_for("posts_detail", post_id=post_id))

        remove_attachment_file(attachment.stored_name)
        db.session.delete(attachment)
        db.session.commit()
        log_action("post_attachment_delete", "post", post_id, meta=f"attachment_id={attachment_id}")
        flash("첨부파일이 삭제되었습니다.", "info")
        return redirect(url_for("posts_detail", post_id=post_id))

    @app.route("/notices")
    def notices_list():
        if current_user.is_authenticated and current_user.role == "admin":
            notices = Notice.query.order_by(Notice.created_at.desc()).all()
        else:
            notices = Notice.query.filter_by(is_published=True).order_by(Notice.created_at.desc()).all()
        return render_template("notices/list.html", notices=notices)

    @app.route("/notices/<int:notice_id>")
    def notices_detail(notice_id):
        notice = db.get_or_404(Notice, notice_id)
        if not notice.is_published and (not current_user.is_authenticated or current_user.role != "admin"):
            flash("게시되지 않은 공지입니다.", "danger")
            return redirect(url_for("notices_list"))
        return render_template("notices/detail.html", notice=notice)

    @app.route("/complaints")
    @login_required
    def complaints_list():
        if current_user.role == "admin":
            complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
        else:
            complaints = Complaint.query.filter_by(user_id=current_user.id).order_by(Complaint.created_at.desc()).all()
        return render_template(
            "complaints/list.html",
            complaints=complaints,
            complaint_category_labels=COMPLAINT_CATEGORY_LABELS,
        )

    @app.route("/complaints/guide")
    def complaints_guide():
        return render_template(
            "complaints/guide.html",
            guide_items=COMPLAINT_TYPE_GUIDE,
        )

    @app.route("/complaints/faq")
    def complaints_faq():
        return render_template(
            "complaints/faq.html",
            status_faq=COMPLAINT_STATUS_FAQ,
            health_faq=HEALTH_FAQ,
        )

    @app.route("/complaints/new", methods=["GET", "POST"])
    @login_required
    def complaints_new():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            category = request.form.get("category", "general").strip()
            patient_name = request.form.get("patient_name", "").strip()
            resident_number = request.form.get("resident_number", "").strip()
            medical_record = request.form.get("medical_record", "").strip()
            errors = validate_title_and_content(title, content)
            errors.extend(validate_complaint_category(category))
            if not patient_name:
                errors.append("이름은 필수 입력값입니다.")
            if not resident_number:
                errors.append("주민번호는 필수 입력값입니다.")
            if resident_number and not re.fullmatch(r"\d{6}-[1-4]\d{6}", resident_number):
                errors.append("주민번호 형식이 올바르지 않습니다. 예: 900101-1234567")
            if errors:
                flash_errors(errors)
                return redirect(url_for("complaints_new"))

            metadata_lines = []
            if patient_name:
                metadata_lines.append(f"[민원인] {patient_name}")
            if resident_number:
                metadata_lines.append(f"[주민번호] {resident_number}")
            if medical_record:
                metadata_lines.append(f"[진료 기록/증상] {medical_record}")
            if metadata_lines:
                content = "\n".join(metadata_lines + ["", content])

            complaint = Complaint(
                title=title,
                content=content,
                category=category,
                user_id=current_user.id,
            )
            db.session.add(complaint)
            db.session.commit()
            log_action("complaint_create", "complaint", complaint.id)
            flash("민원이 접수되었습니다.", "success")
            return redirect(url_for("complaints_list"))

        return render_template("complaints/new.html")

    @app.route("/complaints/<int:complaint_id>", methods=["GET", "POST"])
    @login_required
    def complaints_detail(complaint_id):
        complaint = db.get_or_404(Complaint, complaint_id)
        if current_user.role != "admin" and complaint.user_id != current_user.id:
            flash("열람 권한이 없습니다.", "danger")
            return redirect(url_for("complaints_list"))

        if request.method == "POST":
            if current_user.role != "admin":
                flash("상태 변경 권한이 없습니다.", "danger")
                return redirect(url_for("complaints_detail", complaint_id=complaint_id))
            status = request.form.get("status", complaint.status)
            errors = validate_complaint_status(status)
            if errors:
                flash_errors(errors)
                return redirect(url_for("complaints_detail", complaint_id=complaint_id))
            complaint.status = status
            complaint.assigned_admin_id = current_user.id
            db.session.commit()
            log_action("complaint_status_update", "complaint", complaint.id, meta=complaint.status)
            flash("민원 상태가 변경되었습니다.", "success")
            return redirect(url_for("complaints_detail", complaint_id=complaint_id))

        return render_template(
            "complaints/detail.html",
            complaint=complaint,
            complaint_category_labels=COMPLAINT_CATEGORY_LABELS,
        )

    @app.route("/complaints/<int:complaint_id>/report.pdf")
    @login_required
    def complaint_report_pdf(complaint_id):
        complaint = db.get_or_404(Complaint, complaint_id)
        if current_user.role != "admin" and complaint.user_id != current_user.id:
            flash("리포트 다운로드 권한이 없습니다.", "danger")
            return redirect(url_for("complaints_list"))

        pdf_bytes = build_complaint_report_pdf(complaint)
        log_action("complaint_report_download", "complaint", complaint.id)
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=complaint_{complaint.id}_report.pdf"
            },
        )

    @app.route("/admin")
    @login_required
    @admin_required
    def admin_dashboard():
        stats = {
            "users": User.query.count(),
            "posts": Post.query.count(),
            "notices": Notice.query.count(),
            "complaints": Complaint.query.count(),
            "complaints_pending": Complaint.query.filter(
                Complaint.status.in_(["received", "in_review"])
            ).count(),
        }
        complaint_category_stats = (
            db.session.query(Complaint.category, func.count(Complaint.id))
            .group_by(Complaint.category)
            .order_by(func.count(Complaint.id).desc())
            .all()
        )
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(20).all()
        return render_template(
            "admin/dashboard.html",
            stats=stats,
            logs=logs,
            complaint_category_stats=complaint_category_stats,
            complaint_category_labels=COMPLAINT_CATEGORY_LABELS,
        )

    @app.route("/admin/users", methods=["GET", "POST"])
    @login_required
    @admin_required
    def admin_users():
        page = request.args.get("page", 1, type=int)
        q = request.args.get("q", "").strip()
        role_filter = request.args.get("role", "all")

        if request.method == "POST":
            user_id = request.form.get("user_id", type=int)
            role = request.form.get("role", "user")
            page = request.form.get("page", 1, type=int) or 1
            q = request.form.get("q", "").strip()
            role_filter = request.form.get("role_filter", "all")
            if user_id is None:
                flash("대상 사용자를 확인할 수 없습니다.", "danger")
                return redirect(url_for("admin_users", page=page, q=q, role=role_filter))
            errors = validate_role(role)
            if errors:
                flash_errors(errors)
                return redirect(url_for("admin_users", page=page, q=q, role=role_filter))
            target = db.get_or_404(User, user_id)
            if target.id == current_user.id and role != "admin":
                flash("본인 관리자 권한은 제거할 수 없습니다.", "danger")
                return redirect(url_for("admin_users", page=page, q=q, role=role_filter))
            target.role = role
            db.session.commit()
            log_action("user_role_update", "user", target.id, meta=role)
            flash("사용자 권한이 변경되었습니다.", "success")
            return redirect(url_for("admin_users", page=page, q=q, role=role_filter))

        query = User.query
        if q:
            keyword = f"%{q}%"
            query = query.filter(
                (User.username.ilike(keyword))
                | (User.email.ilike(keyword))
                | (User.full_name.ilike(keyword))
            )
        if role_filter in {"user", "admin"}:
            query = query.filter_by(role=role_filter)

        pagination = query.order_by(User.created_at.desc()).paginate(
            page=parse_page(page),
            per_page=10,
            error_out=False,
        )
        return render_template(
            "admin/users.html",
            users=pagination.items,
            pagination=pagination,
            q=q,
            role_filter=role_filter,
        )

    @app.route("/admin/notices", methods=["GET", "POST"])
    @login_required
    @admin_required
    def admin_notices():
        page = request.args.get("page", 1, type=int)
        q = request.args.get("q", "").strip()
        visibility = request.args.get("visibility", "all")

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            is_published = request.form.get("is_published") == "on"
            page = request.form.get("page", 1, type=int) or 1
            q = request.form.get("q", "").strip()
            visibility = request.form.get("visibility", "all")
            errors = validate_title_and_content(title, content)
            if errors:
                flash_errors(errors)
                return redirect(
                    url_for(
                        "admin_notices",
                        page=page,
                        q=q,
                        visibility=visibility,
                    )
                )

            notice = Notice(
                title=title,
                content=content,
                is_published=is_published,
                created_by=current_user.id,
            )
            db.session.add(notice)
            db.session.commit()
            log_action("notice_create", "notice", notice.id)
            flash("공지사항이 등록되었습니다.", "success")
            return redirect(
                url_for(
                    "admin_notices",
                    page=page,
                    q=q,
                    visibility=visibility,
                )
            )

        query = Notice.query
        if q:
            keyword = f"%{q}%"
            query = query.filter(
                (Notice.title.ilike(keyword))
                | (Notice.content.ilike(keyword))
            )
        if visibility == "published":
            query = query.filter_by(is_published=True)
        elif visibility == "private":
            query = query.filter_by(is_published=False)

        pagination = query.order_by(Notice.created_at.desc()).paginate(
            page=parse_page(page),
            per_page=10,
            error_out=False,
        )
        return render_template(
            "admin/notices.html",
            notices=pagination.items,
            pagination=pagination,
            q=q,
            visibility=visibility,
        )

    @app.route("/admin/notices/<int:notice_id>/publish", methods=["POST"])
    @login_required
    @admin_required
    def admin_notice_publish(notice_id):
        page = request.args.get("page", 1, type=int) or 1
        q = request.args.get("q", "").strip()
        visibility = request.args.get("visibility", "all")
        notice = db.get_or_404(Notice, notice_id)
        notice.is_published = not notice.is_published
        db.session.commit()
        log_action("notice_toggle_publish", "notice", notice.id, meta=str(notice.is_published))
        flash("공지 공개 상태가 변경되었습니다.", "info")
        return redirect(
            url_for(
                "admin_notices",
                page=page,
                q=q,
                visibility=visibility,
            )
        )

    @app.route("/admin/posts")
    @login_required
    @admin_required
    def admin_posts():
        q = request.args.get("q", "").strip()
        category_filter = request.args.get("category", "all")
        query = Post.query.join(User, Post.user_id == User.id)
        if q:
            keyword = f"%{q}%"
            query = query.filter(
                (Post.title.ilike(keyword))
                | (Post.content.ilike(keyword))
                | (User.username.ilike(keyword))
            )
        if category_filter in POST_CATEGORY_SET:
            query = query.filter(Post.category == category_filter)
        else:
            category_filter = "all"

        pagination = query.order_by(Post.created_at.desc()).paginate(
            page=parse_page(),
            per_page=10,
            error_out=False,
        )
        return render_template(
            "admin/posts.html",
            posts=pagination.items,
            pagination=pagination,
            q=q,
            category_filter=category_filter,
            category_options=sorted(POST_CATEGORY_SET),
            post_category_labels=POST_CATEGORY_LABELS,
        )

    @app.route("/admin/logs")
    @login_required
    @admin_required
    def admin_logs():
        q = request.args.get("q", "").strip()
        event_filter = request.args.get("event", "all").strip()
        method_filter = request.args.get("method", "all").upper().strip()

        query = AuditLog.query.outerjoin(User, AuditLog.actor_id == User.id)
        if q:
            keyword = f"%{q}%"
            query = query.filter(
                or_(
                    AuditLog.action.ilike(keyword),
                    AuditLog.target_type.ilike(keyword),
                    AuditLog.target_id.ilike(keyword),
                    AuditLog.meta.ilike(keyword),
                    User.username.ilike(keyword),
                )
            )
        if event_filter in LOG_EVENT_OPTIONS:
            query = query.filter(AuditLog.action == event_filter)
        else:
            event_filter = "all"

        method_options = ["GET", "POST", "PUT", "PATCH", "DELETE"]
        if method_filter in method_options:
            query = query.filter(AuditLog.target_type == method_filter)
        else:
            method_filter = "all"

        pagination = query.order_by(AuditLog.created_at.desc()).paginate(
            page=parse_page(),
            per_page=20,
            error_out=False,
        )
        return render_template(
            "admin/logs.html",
            logs=pagination.items,
            pagination=pagination,
            q=q,
            event_filter=event_filter,
            event_options=sorted(LOG_EVENT_OPTIONS),
            method_filter=method_filter,
            method_options=method_options,
        )

    @app.route("/admin/complaints")
    @login_required
    @admin_required
    def admin_complaints():
        q = request.args.get("q", "").strip()
        status_filter = request.args.get("status", "all")
        category_filter = request.args.get("category", "all")

        query = Complaint.query.join(User, Complaint.user_id == User.id)
        if q:
            keyword = f"%{q}%"
            query = query.filter(
                (Complaint.title.ilike(keyword))
                | (Complaint.content.ilike(keyword))
                | (User.username.ilike(keyword))
            )
        if status_filter in COMPLAINT_STATUS_SET:
            query = query.filter(Complaint.status == status_filter)
        if category_filter in COMPLAINT_CATEGORY_SET:
            query = query.filter(Complaint.category == category_filter)

        pagination = query.order_by(Complaint.created_at.desc()).paginate(
            page=parse_page(),
            per_page=10,
            error_out=False,
        )
        return render_template(
            "admin/complaints.html",
            complaints=pagination.items,
            pagination=pagination,
            q=q,
            status_filter=status_filter,
            category_filter=category_filter,
            status_options=sorted(COMPLAINT_STATUS_SET),
            category_options=sorted(COMPLAINT_CATEGORY_SET),
            complaint_category_labels=COMPLAINT_CATEGORY_LABELS,
        )

    @app.route("/security/scenarios")
    @login_required
    @admin_required
    def security_scenarios():
        return render_template(
            "security/list.html",
            scenarios=OWASP_TOP10_SCENARIOS,
        )

    @app.route("/security/scenarios/<string:scenario_id>")
    @login_required
    @admin_required
    def security_scenario_detail(scenario_id):
        scenario = next(
            (
                item
                for item in OWASP_TOP10_SCENARIOS
                if item["id"] == scenario_id
            ),
            None,
        )
        if scenario is None:
            abort(404)
        return render_template(
            "security/detail.html",
            scenario=scenario,
        )

    # ── VulnLab ──────────────────────────────────────────────────────────────────

    @app.route("/vulnlab/")
    @login_required
    def vulnlab_index():
        return render_template("vulnlab/index.html")

    @app.route("/vulnlab/a01")
    @login_required
    def vulnlab_a01():
        target_id = request.args.get("user_id", type=int)
        target_user = None
        if target_id is not None:
            target_user = db.session.get(User, target_id)
        all_users = User.query.with_entities(User.id, User.username).all()
        return render_template(
            "vulnlab/a01.html",
            target_user=target_user,
            all_users=all_users,
            target_id=target_id,
        )

    @app.route("/vulnlab/a02")
    @login_required
    def vulnlab_a02():
        import traceback as _tb
        secret_key = current_app.config.get("SECRET_KEY", "unknown")
        debug_mode = current_app.config.get("DEBUG", False)
        db_url = current_app.config.get("SQLALCHEMY_DATABASE_URI", "unknown")
        error_detail = None
        if request.args.get("trigger_error"):
            try:
                _ = 1 / 0
            except ZeroDivisionError:
                error_detail = _tb.format_exc()
        return render_template(
            "vulnlab/a02.html",
            secret_key=secret_key,
            debug_mode=debug_mode,
            db_url=db_url,
            error_detail=error_detail,
        )

    @app.route("/vulnlab/a03")
    @login_required
    def vulnlab_a03():
        req_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "requirements.txt")
        )
        requirements = []
        try:
            with open(req_path) as _f:
                for line in _f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        requirements.append(line)
        except Exception:
            requirements = ["(requirements.txt 읽기 실패)"]
        pip_output = ""
        try:
            result = subprocess.run(
                ["pip", "list", "--format=columns"],
                capture_output=True, text=True, timeout=10
            )
            pip_output = result.stdout
        except Exception as _e:
            pip_output = f"오류: {_e}"
        return render_template(
            "vulnlab/a03.html",
            requirements=requirements,
            pip_output=pip_output,
        )

    @app.route("/vulnlab/a04", methods=["GET", "POST"])
    @login_required
    def vulnlab_a04():
        results = None
        hash_input = ""
        if request.method == "POST":
            hash_input = request.form.get("hash_input", "")
            results = {
                "plaintext": hash_input,
                "md5": hashlib.md5(hash_input.encode()).hexdigest(),
                "sha1": hashlib.sha1(hash_input.encode()).hexdigest(),
                "sha256": hashlib.sha256(hash_input.encode()).hexdigest(),
                "pbkdf2": hashlib.pbkdf2_hmac(
                    "sha256", hash_input.encode(), b"salt", 100000
                ).hex(),
            }
        return render_template("vulnlab/a04.html", results=results, hash_input=hash_input)

    @app.route("/vulnlab/a05")
    @login_required
    def vulnlab_a05():
        search = request.args.get("q", "")
        vuln_rows = []
        safe_rows = []
        vuln_error = None
        if search:
            try:
                vuln_sql = (
                    f"SELECT id,username,email,role FROM user"
                    f" WHERE username LIKE '%{search}%'"
                )
                vuln_rows = db.session.execute(text(vuln_sql)).fetchall()
            except Exception as _e:
                vuln_error = str(_e)
            try:
                safe_sql = (
                    "SELECT id,username,email,role FROM user WHERE username LIKE :s"
                )
                safe_rows = db.session.execute(
                    text(safe_sql), {"s": f"%{search}%"}
                ).fetchall()
            except Exception:
                safe_rows = []
        return render_template(
            "vulnlab/a05.html",
            search=search,
            vuln_rows=vuln_rows,
            safe_rows=safe_rows,
            vuln_error=vuln_error,
        )

    @app.route("/vulnlab/a06", methods=["GET", "POST"])
    @login_required
    def vulnlab_a06():
        ip = request.remote_addr or "unknown"
        now_ts = time.time()
        window = 60
        if ip not in _vulnlab_a06_request_log:
            _vulnlab_a06_request_log[ip] = []
        _vulnlab_a06_request_log[ip] = [
            t for t in _vulnlab_a06_request_log[ip] if now_ts - t < window
        ]
        status_update_msg = None
        if request.method == "POST":
            action = request.form.get("action")
            if action == "request":
                _vulnlab_a06_request_log[ip].append(now_ts)
            elif action == "status_jump":
                complaint_id = request.form.get("complaint_id", type=int)
                new_status = request.form.get("new_status", "")
                if complaint_id and new_status in COMPLAINT_STATUS_SET:
                    c = db.session.get(Complaint, complaint_id)
                    if c:
                        old_status = c.status
                        c.status = new_status
                        db.session.commit()
                        status_update_msg = f"민원 #{complaint_id} 상태: {old_status} → {new_status}"
                    else:
                        status_update_msg = f"민원 #{complaint_id} 찾을 수 없음"
                else:
                    status_update_msg = "유효하지 않은 입력"
        request_count = len(_vulnlab_a06_request_log[ip])
        complaints = (
            Complaint.query.filter_by(user_id=current_user.id)
            .order_by(Complaint.created_at.desc())
            .limit(5)
            .all()
        )
        return render_template(
            "vulnlab/a06.html",
            request_count=request_count,
            window=window,
            status_update_msg=status_update_msg,
            complaints=complaints,
        )

    @app.route("/vulnlab/a07", methods=["GET", "POST"])
    @login_required
    def vulnlab_a07():
        brute_results = []
        target_username = ""
        if request.method == "POST":
            target_username = request.form.get("target_username", "")
            common_passwords = [
                "password", "123456", "admin", "user12345",
                "admin1234", "qwerty", "letmein", "abc123",
            ]
            target_u = User.query.filter_by(username=target_username).first()
            for pw in common_passwords:
                matched = bool(target_u and target_u.check_password(pw))
                brute_results.append({"password": pw, "matched": matched})
            ip_key = request.remote_addr or "unknown"
            _vulnlab_a07_attempt_log[ip_key] = (
                _vulnlab_a07_attempt_log.get(ip_key, 0) + len(common_passwords)
            )
        attempt_count = _vulnlab_a07_attempt_log.get(request.remote_addr or "", 0)
        raw_cookie = request.cookies.get("session", "(없음)")
        session_cookie = (raw_cookie[:30] + "...") if len(raw_cookie) > 30 else raw_cookie
        return render_template(
            "vulnlab/a07.html",
            brute_results=brute_results,
            target_username=target_username,
            attempt_count=attempt_count,
            session_cookie=session_cookie,
        )

    @app.route("/vulnlab/a08", methods=["GET", "POST"])
    @login_required
    def vulnlab_a08():
        generated_payload = None
        vuln_result = None
        safe_result = None
        error_msg = None
        if request.method == "POST":
            action = request.form.get("action")
            if action == "generate":
                class _SafeDemoObj:
                    def __init__(self):
                        self.name = "안전한 데모 객체"
                        self.value = 42
                        self.message = "이 객체는 pickle로 직렬화됩니다"
                raw = pickle.dumps(_SafeDemoObj())
                generated_payload = base64.b64encode(raw).decode()
            elif action == "vuln_deserialize":
                b64_input = request.form.get("b64_input", "")
                try:
                    raw = base64.b64decode(b64_input)
                    obj = pickle.loads(raw)  # noqa: S301
                    obj_repr = vars(obj) if hasattr(obj, "__dict__") else str(obj)
                    vuln_result = f"역직렬화 성공: {obj.__class__.__name__} - {obj_repr}"
                except Exception as _e:
                    error_msg = f"역직렬화 오류: {_e}"
            elif action == "safe_json":
                json_input = request.form.get("json_input", "{}")
                try:
                    obj = json.loads(json_input)
                    safe_result = f"JSON 파싱 성공: {obj}"
                except Exception as _e:
                    safe_result = f"JSON 파싱 오류: {_e}"
        return render_template(
            "vulnlab/a08.html",
            generated_payload=generated_payload,
            vuln_result=vuln_result,
            safe_result=safe_result,
            error_msg=error_msg,
        )

    @app.route("/vulnlab/a09", methods=["GET", "POST"])
    @login_required
    def vulnlab_a09():
        logs = (
            AuditLog.query.filter_by(actor_id=current_user.id)
            .order_by(AuditLog.created_at.desc())
            .limit(20)
            .all()
        )
        log_result = None
        if request.method == "POST":
            fake_password = request.form.get("fake_password", "")
            log_action(
                "vulnlab_sensitive_log",
                meta={"password_plaintext": fake_password, "user": current_user.username},
            )
            log_action(
                "vulnlab_masked_log",
                meta={"password": "****", "user": current_user.username},
            )
            db.session.commit()
            log_result = {
                "vuln_log": (
                    f'{{"event":"login","user":"{current_user.username}",'
                    f'"password":"{fake_password}"}}'
                ),
                "safe_log": (
                    f'{{"event":"login","user":"{current_user.username}",'
                    f'"password":"****"}}'
                ),
            }
            logs = (
                AuditLog.query.filter_by(actor_id=current_user.id)
                .order_by(AuditLog.created_at.desc())
                .limit(20)
                .all()
            )
        failed_count = AuditLog.query.filter_by(action="login_failed").count()
        return render_template(
            "vulnlab/a09.html",
            logs=logs,
            log_result=log_result,
            failed_count=failed_count,
        )

    @app.route("/vulnlab/a10", methods=["GET", "POST"])
    @login_required
    def vulnlab_a10():
        import traceback as _tb
        exception_result = None
        null_result = None
        if request.method == "POST":
            action = request.form.get("action")
            if action == "divide":
                divisor_str = request.form.get("divisor", "")
                try:
                    divisor = int(divisor_str)
                    result = 100 / divisor
                    exception_result = {
                        "vuln": f"100 / {divisor} = {result}",
                        "safe": f"100 / {divisor} = {result}",
                    }
                except ZeroDivisionError:
                    exception_result = {
                        "vuln": _tb.format_exc(),
                        "safe": "오류: 0으로 나눌 수 없습니다.",
                    }
                except ValueError:
                    exception_result = {
                        "vuln": _tb.format_exc(),
                        "safe": "오류: 숫자를 입력해주세요.",
                    }
            elif action == "null_input":
                value = request.form.get("value", "")
                if not value:
                    null_result = {
                        "vuln": "AttributeError: 'NoneType' object has no attribute 'upper'",
                        "safe": "입력값이 없습니다.",
                    }
                else:
                    null_result = {"vuln": value.upper(), "safe": value.upper()}
        admin_required_source = (
            "def admin_required(func):\n"
            "    @wraps(func)\n"
            "    def wrapped(*args, **kwargs):\n"
            "        #if not current_user.is_authenticated or current_user.role != 'admin':\n"
            "        #    flash('관리자만 접근 가능합니다.', 'danger')\n"
            "        #    return redirect(url_for('index'))\n"
            "        return func(*args, **kwargs)  # ← Fail-Open!\n"
            "    return wrapped"
        )
        return render_template(
            "vulnlab/a10.html",
            exception_result=exception_result,
            null_result=null_result,
            admin_required_source=admin_required_source,
        )

    # ── 추가 취약점 시나리오 ───────────────────────────────────────────────────────

    # 암호화2: MD5 비밀번호 저장 + SQL Injection 연동
    @app.route("/vulnlab/crypto2")
    @login_required
    def vulnlab_crypto2():
        search = request.args.get("q", "")
        vuln_rows = []
        vuln_error = None
        if search:
            try:
                vuln_sql = (
                    f"SELECT id,username,password_hash,email,role FROM user"
                    f" WHERE username LIKE '%{search}%'"
                )
                vuln_rows = db.session.execute(text(vuln_sql)).fetchall()
            except Exception as _e:
                vuln_error = str(_e)
        return render_template(
            "vulnlab/crypto2.html",
            search=search,
            vuln_rows=vuln_rows,
            vuln_error=vuln_error,
            demo_users=_DEMO_MD5_USERS,
        )

    # 암호화3: 파일 다운로드 IDOR (파일명에 개인정보 + 소유권 체크 없음)
    @app.route("/vulnlab/crypto3")
    @login_required
    def vulnlab_crypto3():
        my_file = list(_FAKE_PATIENT_FILES.keys())[0]
        return render_template(
            "vulnlab/crypto3.html",
            my_file=my_file,
            all_files=list(_FAKE_PATIENT_FILES.keys()),
        )

    @app.route("/vulnlab/crypto3/download")
    @login_required
    def vulnlab_crypto3_download():
        file_name = request.args.get("file_name", "")
        if not file_name:
            return redirect(url_for("vulnlab_crypto3"))
        # 취약: 파일명 소유권 체크 없음, 경로 그대로 노출
        content = _FAKE_PATIENT_FILES.get(file_name)
        if content is None:
            return f"파일을 찾을 수 없습니다: {file_name}", 404
        return Response(
            content,
            mimetype="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )

    # 인증2: 순차 세션 ID 취약점 데모
    @app.route("/vulnlab/auth2", methods=["GET", "POST"])
    @login_required
    def vulnlab_auth2():
        session_info = None
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            if username:
                _weak_session_counter[0] += 1
                sid = _weak_session_counter[0]
                _weak_sessions[sid] = {
                    "username": username,
                    "role": "admin" if "admin" in username else "user",
                    "email": f"{username}@hospital.kr",
                    "complaints": f"민원 {sid * 3}건",
                }
                session_info = {"session_id": sid, "user": _weak_sessions[sid]}
        return render_template(
            "vulnlab/auth2.html",
            session_info=session_info,
            sessions=dict(_weak_sessions),
        )

    @app.route("/vulnlab/auth2/profile")
    @login_required
    def vulnlab_auth2_profile():
        try:
            sid = int(request.args.get("session_id", 0))
        except ValueError:
            return render_template("vulnlab/auth2_profile.html", user_info=None, session_id=0)
        user_info = _weak_sessions.get(sid)
        return render_template(
            "vulnlab/auth2_profile.html",
            user_info=user_info,
            session_id=sid,
        )

    # 인증3: @login_required 고의 누락 – 인증 없이 전체 사용자 목록 접근
    @app.route("/vulnlab/auth3/user-list")
    # @login_required  ← 고의로 누락! (인증 우회 취약점 시연)
    def vulnlab_auth3_userlist():
        users = User.query.with_entities(
            User.id, User.username, User.email,
            User.full_name, User.phone, User.role,
        ).all()
        return render_template("vulnlab/auth3.html", users=users)

    @app.errorhandler(404)
    def not_found_error(_):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(_):
        db.session.rollback()
        return render_template("errors/500.html"), 500
