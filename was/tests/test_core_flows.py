import json
import io
from datetime import datetime

from app import create_app, db
from app.models import (
    AuditLog,
    Complaint,
    MyDataSnapshot,
    Notice,
    Post,
    PostAttachment,
    User,
)


def _create_user(username, role="user"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=f"{username} name",
        phone="010-9999-9999",
        role=role,
    )
    user.set_password("pass12345")
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, username, password="pass12345"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def test_register_login_logout_flow(tmp_path):
    db_path = tmp_path / "flow.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()

    client = app.test_client()

    res = client.post(
        "/register",
        data={
            "username": "usernew",
            "email": "usernew@example.com",
            "full_name": "User New",
            "phone": "010-1111-2222",
            "password": "pass12345",
            "agree_required_terms": "on",
            "agree_optional_terms": "on",
        },
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]

    res = _login(client, "usernew")
    assert res.status_code == 302
    assert res.headers["Location"].endswith("/")

    res = client.get("/logout", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["Location"].endswith("/")


def test_register_duplicate_check_endpoint(tmp_path):
    db_path = tmp_path / "register_dup_check.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()
        _create_user("dupuser", role="user")

    client = app.test_client()
    used_username = client.get("/register/check-duplicate?field=username&value=dupuser")
    assert used_username.status_code == 200
    assert used_username.get_json()["available"] is False

    available_username = client.get("/register/check-duplicate?field=username&value=newuserok")
    assert available_username.status_code == 200
    assert available_username.get_json()["available"] is True

    used_email = client.get("/register/check-duplicate?field=email&value=dupuser@example.com")
    assert used_email.status_code == 200
    assert used_email.get_json()["available"] is False

    bad_field = client.get("/register/check-duplicate?field=phone&value=010")
    assert bad_field.status_code == 400



def test_admin_page_blocked_for_normal_user(tmp_path):
    db_path = tmp_path / "authz.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()
        _create_user("normal", role="user")

    client = app.test_client()
    _login(client, "normal")

    res = client.get("/admin", follow_redirects=False)
    assert res.status_code == 302



def test_private_notice_is_hidden_for_normal_user(tmp_path):
    db_path = tmp_path / "notice.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()
        admin = _create_user("adminx", role="admin")
        user = _create_user("member", role="user")
        private_notice = Notice(
            title="private",
            content="hidden",
            is_published=False,
            created_by=admin.id,
        )
        db.session.add(private_notice)
        db.session.commit()

        private_id = private_notice.id
        del user

    client = app.test_client()
    _login(client, "member")

    res = client.get(f"/notices/{private_id}", follow_redirects=False)
    assert res.status_code == 302
    assert "/notices" in res.headers["Location"]



def test_complaint_status_update_admin_only(tmp_path):
    db_path = tmp_path / "complaint.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()
        admin = _create_user("opsadmin", role="admin")
        user = _create_user("requester", role="user")
        complaint = Complaint(
            title="help",
            content="need support",
            category="general",
            user_id=user.id,
        )
        db.session.add(complaint)
        db.session.commit()
        complaint_id = complaint.id
        admin_name = admin.username

    user_client = app.test_client()
    _login(user_client, "requester")
    res = user_client.post(
        f"/complaints/{complaint_id}", data={"status": "resolved"}, follow_redirects=False
    )
    assert res.status_code == 302

    admin_client = app.test_client()
    _login(admin_client, admin_name)
    res = admin_client.post(
        f"/complaints/{complaint_id}", data={"status": "resolved"}, follow_redirects=False
    )
    assert res.status_code == 302

    with app.app_context():
        updated = db.session.get(Complaint, complaint_id)
        assert updated.status == "resolved"


def test_complaint_access_owner_admin_only(tmp_path):
    db_path = tmp_path / "complaint_access.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()
        owner = _create_user("owner_user", role="user")
        stranger = _create_user("stranger_user", role="user")
        admin = _create_user("admin_user", role="admin")
        complaint = Complaint(
            title="owner complaint only",
            content="private complaint content",
            category="privacy",
            user_id=owner.id,
        )
        db.session.add(complaint)
        db.session.commit()
        complaint_id = complaint.id
        del stranger
        del admin

    stranger_client = app.test_client()
    _login(stranger_client, "stranger_user")
    blocked_detail = stranger_client.get(f"/complaints/{complaint_id}", follow_redirects=False)
    blocked_report = stranger_client.get(f"/complaints/{complaint_id}/report.pdf", follow_redirects=False)
    assert blocked_detail.status_code == 302
    assert blocked_report.status_code == 302

    owner_client = app.test_client()
    _login(owner_client, "owner_user")
    owner_detail = owner_client.get(f"/complaints/{complaint_id}", follow_redirects=False)
    assert owner_detail.status_code == 200

    admin_client = app.test_client()
    _login(admin_client, "admin_user")
    admin_detail = admin_client.get(f"/complaints/{complaint_id}", follow_redirects=False)
    assert admin_detail.status_code == 200


def test_security_scenarios_admin_only(tmp_path):
    db_path = tmp_path / "security.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()
        _create_user("secmember", role="user")
        _create_user("secadmin", role="admin")

    user_client = app.test_client()
    _login(user_client, "secmember")
    blocked = user_client.get("/security/scenarios", follow_redirects=False)
    assert blocked.status_code == 302

    admin_client = app.test_client()
    _login(admin_client, "secadmin")
    allowed = admin_client.get("/security/scenarios", follow_redirects=False)
    assert allowed.status_code == 200
    assert b"A01:2025" in allowed.data


def test_admin_users_search_filter_and_pagination(tmp_path):
    db_path = tmp_path / "admin_users.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()
        _create_user("filteradmin", role="admin")
        for idx in range(12):
            _create_user(f"user{idx:02d}", role="user")

    client = app.test_client()
    _login(client, "filteradmin")

    filtered = client.get("/admin/users?q=user0&role=user&page=1", follow_redirects=False)
    assert filtered.status_code == 200
    assert b"user00" in filtered.data

    page2 = client.get("/admin/users?page=2", follow_redirects=False)
    assert page2.status_code == 200
    assert "페이지 2".encode() in page2.data


def test_health_info_pages_public(tmp_path):
    db_path = tmp_path / "health_pages.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()

    client = app.test_client()
    info = client.get("/health-info", follow_redirects=False)
    assert info.status_code == 200
    assert "주요 공공 의료 소식".encode() in info.data

    centers = client.get("/health-centers", follow_redirects=False)
    assert centers.status_code == 200

    detail = client.get("/health-programs/vaccination", follow_redirects=False)
    assert detail.status_code == 200
    missing = client.get("/health-programs/not-exists", follow_redirects=False)
    assert missing.status_code == 404


def test_posts_category_filter(tmp_path):
    db_path = tmp_path / "post_category.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()
        user = _create_user("writer", role="user")
        db.session.add(
            Post(
                title="digital complaint",
                content="portal issue",
                category="digital_service",
                user_id=user.id,
            )
        )
        db.session.add(
            Post(
                title="billing complaint",
                content="billing issue",
                category="insurance_billing",
                user_id=user.id,
            )
        )
        db.session.commit()

    client = app.test_client()
    filtered = client.get("/posts?category=digital_service", follow_redirects=False)
    assert filtered.status_code == 200
    assert b"digital complaint" in filtered.data
    assert b"billing complaint" not in filtered.data


def test_admin_logs_page_access_and_filter(tmp_path):
    db_path = tmp_path / "admin_logs.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()
        _create_user("logmember", role="user")
        admin = _create_user("logadmin", role="admin")
        db.session.add(
            AuditLog(
                actor_id=admin.id,
                action="login",
                target_type="user",
                target_id=str(admin.id),
            )
        )
        db.session.add(
            AuditLog(
                actor_id=admin.id,
                action="web_request",
                target_type="GET",
                target_id="/posts",
                meta="status=200",
            )
        )
        db.session.commit()

    admin_client = app.test_client()
    _login(admin_client, "logadmin")
    log_page = admin_client.get(
        "/admin/logs?event=web_request&method=GET&q=/posts",
        follow_redirects=False,
    )
    assert log_page.status_code == 200
    assert b"web_request" in log_page.data
    assert b"/posts" in log_page.data

    user_client = app.test_client()
    _login(user_client, "logmember")
    blocked = user_client.get("/admin/logs", follow_redirects=False)
    assert blocked.status_code == 302


def test_login_failed_attempt_is_logged(tmp_path):
    db_path = tmp_path / "login_failed_logs.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()
        _create_user("authuser", role="user")

    client = app.test_client()
    failed = _login(client, "authuser", password="wrong-pass")
    assert failed.status_code == 200

    with app.app_context():
        failed_log = (
            AuditLog.query.filter_by(action="login_failed")
            .order_by(AuditLog.id.desc())
            .first()
        )
        attempt_log = (
            AuditLog.query.filter_by(action="login_attempt")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert failed_log is not None
        assert failed_log.target_type == "POST"
        assert failed_log.target_id == "authuser"
        assert "result=failed" in (failed_log.meta or "")
        assert "reason=invalid_password" in (failed_log.meta or "")

        assert attempt_log is not None
        assert attempt_log.target_type == "POST"
        assert attempt_log.target_id == "authuser"
        assert "result=failed" in (attempt_log.meta or "")


def test_admin_logs_kst_rendering(tmp_path):
    db_path = tmp_path / "admin_logs_kst.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()
        admin = _create_user("kstadmin", role="admin")
        db.session.add(
            AuditLog(
                actor_id=admin.id,
                action="login_attempt",
                target_type="POST",
                target_id="kstadmin",
                meta="endpoint=/login;result=success",
                created_at=datetime(2026, 2, 10, 0, 0, 0),
            )
        )
        db.session.commit()

    client = app.test_client()
    _login(client, "kstadmin")
    log_page = client.get("/admin/logs?event=login_attempt", follow_redirects=False)
    assert log_page.status_code == 200
    assert "2026-02-10 09:00:00".encode() in log_page.data


def test_profile_mydata_fetch_and_render(tmp_path):
    db_path = tmp_path / "mydata.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()
        _create_user("mydatauser", role="user")

    client = app.test_client()
    _login(client, "mydatauser")

    blocked = client.post("/profile/mydata/fetch", data={}, follow_redirects=False)
    assert blocked.status_code == 302

    fetched = client.post(
        "/profile/mydata/fetch",
        data={"consent_mydata": "on"},
        follow_redirects=False,
    )
    assert fetched.status_code == 302

    with app.app_context():
        snapshot = (
            MyDataSnapshot.query.order_by(MyDataSnapshot.fetched_at.desc()).first()
        )
        assert snapshot is not None
        payload = json.loads(snapshot.payload_json)
        assert payload["source"] == "MOCK"
        assert len(payload["visits"]) >= 1

    profile_page = client.get("/profile", follow_redirects=False)
    assert profile_page.status_code == 200
    assert "의료 마이데이터".encode() in profile_page.data


def test_post_attachment_upload_download_delete(tmp_path):
    db_path = tmp_path / "post_attachment.db"
    upload_dir = tmp_path / "uploads"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
            "POST_UPLOAD_DIR": str(upload_dir),
        }
    )

    with app.app_context():
        db.create_all()
        _create_user("attachuser", role="user")

    client = app.test_client()
    _login(client, "attachuser")

    create_res = client.post(
        "/posts/new",
        data={
            "title": "첨부파일 테스트",
            "content": "첨부 테스트 본문",
            "category": "general",
            "attachments": (io.BytesIO(b"hello attachment"), "sample.txt"),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert create_res.status_code == 302

    with app.app_context():
        post = Post.query.filter_by(title="첨부파일 테스트").first()
        assert post is not None
        attachment = PostAttachment.query.filter_by(post_id=post.id).first()
        assert attachment is not None
        attachment_id = attachment.id
        post_id = post.id

    download = client.get(
        f"/posts/{post_id}/attachments/{attachment_id}",
        follow_redirects=False,
    )
    assert download.status_code == 200
    assert b"hello attachment" in download.data

    delete_res = client.post(
        f"/posts/{post_id}/attachments/{attachment_id}/delete",
        follow_redirects=False,
    )
    assert delete_res.status_code == 302

    with app.app_context():
        deleted = PostAttachment.query.filter_by(id=attachment_id).first()
        assert deleted is None


def test_health_enhancement_pages_public(tmp_path):
    db_path = tmp_path / "health_plus.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()

    client = app.test_client()
    assert client.get("/complaints/guide", follow_redirects=False).status_code == 200
    assert client.get("/complaints/faq", follow_redirects=False).status_code == 200
    assert client.get("/health-calendar", follow_redirects=False).status_code == 200
    assert client.get("/support-programs", follow_redirects=False).status_code == 200
    assert client.get("/records/procedure", follow_redirects=False).status_code == 200


def test_complaint_report_pdf_download(tmp_path):
    db_path = tmp_path / "complaint_report.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
        }
    )

    with app.app_context():
        db.create_all()
        user = _create_user("reportuser", role="user")
        db.session.add(
            Complaint(
                title="report 대상 민원",
                content="민원 결과 리포트 PDF 테스트",
                category="general",
                user_id=user.id,
            )
        )
        db.session.commit()
        complaint_id = Complaint.query.filter_by(user_id=user.id).first().id

    client = app.test_client()
    _login(client, "reportuser")
    response = client.get(
        f"/complaints/{complaint_id}/report.pdf",
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")


def test_profile_update_requires_password_and_supports_image_terms_and_lists(tmp_path):
    db_path = tmp_path / "profile_update.db"
    upload_dir = tmp_path / "profile_uploads"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret",
            "PROFILE_UPLOAD_DIR": str(upload_dir),
        }
    )

    with app.app_context():
        db.create_all()
        user = _create_user("profileuser", role="user")
        db.session.add(
            Post(
                title="내 작성 게시글",
                content="profile linked post",
                category="general",
                user_id=user.id,
            )
        )
        db.session.add(
            Complaint(
                title="내 작성 민원",
                content="profile linked complaint",
                category="general",
                user_id=user.id,
            )
        )
        db.session.commit()

    client = app.test_client()
    _login(client, "profileuser")

    bad_update = client.post(
        "/profile",
        data={
            "full_name": "New Name",
            "phone": "010-1234-5678",
            "email": "new-profile@example.com",
            "agree_optional_terms": "on",
            "current_password": "wrongpass",
        },
        follow_redirects=False,
    )
    assert bad_update.status_code == 302

    with app.app_context():
        user = User.query.filter_by(username="profileuser").first()
        assert user.full_name == "profileuser name"
        assert user.optional_terms_agreed is False

    good_update = client.post(
        "/profile",
        data={
            "full_name": "New Name",
            "phone": "010-1234-5678",
            "email": "new-profile@example.com",
            "agree_optional_terms": "on",
            "current_password": "pass12345",
            "profile_image": (io.BytesIO(b"fakeimagebytes"), "avatar.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert good_update.status_code == 302

    with app.app_context():
        user = User.query.filter_by(username="profileuser").first()
        assert user.full_name == "New Name"
        assert user.phone == "010-1234-5678"
        assert user.email == "new-profile@example.com"
        assert user.optional_terms_agreed is True
        assert user.optional_terms_agreed_at is not None
        assert user.profile_image_name is not None
        saved_image = upload_dir / user.profile_image_name
        assert saved_image.exists()

    remove_update = client.post(
        "/profile",
        data={
            "full_name": "New Name",
            "phone": "010-1234-5678",
            "email": "new-profile@example.com",
            "current_password": "pass12345",
            "remove_profile_image": "on",
        },
        follow_redirects=False,
    )
    assert remove_update.status_code == 302

    with app.app_context():
        user = User.query.filter_by(username="profileuser").first()
        assert user.optional_terms_agreed is False
        assert user.optional_terms_agreed_at is None
        assert user.profile_image_name is None

    profile_page = client.get("/profile", follow_redirects=False)
    assert profile_page.status_code == 200
    assert "내 작성 게시글".encode() in profile_page.data
    assert "내 작성 민원".encode() in profile_page.data
