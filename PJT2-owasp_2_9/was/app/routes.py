import json
from functools import wraps

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, or_

from app import db
from app.health_content import HEALTH_FAQ, HEALTH_NEWS, HEALTH_PROGRAMS, REGIONAL_CENTERS
from app.models import AuditLog, Complaint, MyDataSnapshot, Notice, Post, User, utc_now
from app.mydata_mock import generate_mock_medical_mydata
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
    "login",
    "login_failed",
    "logout",
    "profile_update",
    "post_create",
    "post_update",
    "post_delete",
    "complaint_create",
    "complaint_status_update",
    "notice_create",
    "notice_toggle_publish",
    "user_role_update",
    "web_request",
    "mydata_fetch",
}


def admin_required(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("관리자만 접근 가능합니다.", "danger")
            return redirect(url_for("index"))
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


def flash_errors(errors):
    for message in errors:
        flash(message, "danger")


def parse_page(default=1):
    page = request.args.get("page", default, type=int)
    return page if page and page > 0 else default


def init_routes(app):
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

            errors = validate_registration(username, email, full_name, phone, password)
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
                role="user",
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("회원가입이 완료되었습니다. 로그인하세요.", "success")
            return redirect(url_for("login"))

        return render_template("auth/register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                login_user(user)
                log_action("login", "user", user.id)
                flash("로그인 성공", "success")
                return redirect(url_for("index"))

            attempted_id = username[:50] if username else None
            client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or "-"
            log_action("login_failed", "user", attempted_id, meta=f"ip={client_ip}", actor_id=None)
            flash("아이디 또는 비밀번호가 잘못되었습니다.", "danger")

        return render_template("auth/login.html")

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
            errors = validate_profile(full_name, phone)
            if errors:
                flash_errors(errors)
                return redirect(url_for("profile"))

            current_user.full_name = full_name
            current_user.phone = phone
            db.session.commit()
            log_action("profile_update", "user", current_user.id)
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
        return render_template(
            "auth/profile.html",
            mydata_snapshot=snapshot,
            mydata=mydata,
        )

    @app.route("/profile/mydata/fetch", methods=["POST"])
    @login_required
    def profile_mydata_fetch():
        consent_given = request.form.get("consent_mydata") == "on"
        if not consent_given:
            flash("의료 마이데이터 불러오기 전에 수집/이용 동의가 필요합니다.", "danger")
            return redirect(url_for("profile"))

        payload = generate_mock_medical_mydata(current_user)
        snapshot = MyDataSnapshot(
            user_id=current_user.id,
            source="MOCK",
            consent_given=True,
            consent_at=utc_now(),
            payload_json=json.dumps(payload, ensure_ascii=False),
            fetched_at=utc_now(),
        )
        db.session.add(snapshot)
        db.session.commit()
        log_action("mydata_fetch", "mydata", snapshot.id, meta="source=MOCK")
        flash("의료 마이데이터를 불러왔습니다. (목데이터)", "success")
        return redirect(url_for("profile"))

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
            errors = validate_title_and_content(title, content)
            errors.extend(validate_post_category(category))
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
            db.session.commit()
            log_action("post_create", "post", post.id)
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
            errors = validate_title_and_content(title, content)
            errors.extend(validate_post_category(category))
            if errors:
                flash_errors(errors)
                return redirect(url_for("posts_detail", post_id=post_id))

            post.title = title
            post.content = content
            post.category = category
            db.session.commit()
            log_action("post_update", "post", post.id)
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

        db.session.delete(post)
        db.session.commit()
        log_action("post_delete", "post", post_id)
        flash("게시물이 삭제되었습니다.", "info")
        return redirect(url_for("posts_list"))

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

    @app.route("/complaints/new", methods=["GET", "POST"])
    @login_required
    def complaints_new():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            category = request.form.get("category", "general").strip()
            errors = validate_title_and_content(title, content)
            errors.extend(validate_complaint_category(category))
            if errors:
                flash_errors(errors)
                return redirect(url_for("complaints_new"))

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

    @app.errorhandler(404)
    def not_found_error(_):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(_):
        db.session.rollback()
        return render_template("errors/500.html"), 500
