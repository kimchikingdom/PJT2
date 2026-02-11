import os
import json

from app import create_app, db
from app.models import Complaint, MyDataSnapshot, Notice, Post, User, utc_now
from app.provider_service import ensure_provider_subjects, portal_fetch_mydata_via_provider_api
from sqlalchemy import inspect, text

app = create_app()


@app.cli.command("init-db")
def init_db_cli():
    db.create_all()
    ensure_schema_upgrades()
    ensure_default_admin()
    ensure_provider_subjects(app.config.get("PROVIDER_SEED_SUBJECTS", 100))
    print("Database initialized.")


def ensure_default_admin():
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@example.com",
            full_name="System Admin",
            phone="010-0000-0000",
            required_terms_agreed=True,
            required_terms_agreed_at=utc_now(),
            role="admin",
        )
        admin.set_password("admin1234")
        db.session.add(admin)
        db.session.commit()
    elif not admin.required_terms_agreed:
        admin.required_terms_agreed = True
        admin.required_terms_agreed_at = admin.required_terms_agreed_at or utc_now()
        db.session.commit()
    return admin


def ensure_user(username, email, full_name, phone, password):
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            phone=phone,
            required_terms_agreed=True,
            required_terms_agreed_at=utc_now(),
            role="user",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    elif not user.required_terms_agreed:
        user.required_terms_agreed = True
        user.required_terms_agreed_at = user.required_terms_agreed_at or utc_now()
        db.session.commit()
    return user


def ensure_schema_upgrades():
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "post" in tables:
        post_columns = {col["name"] for col in inspector.get_columns("post")}
        if "category" not in post_columns:
            db.session.execute(
                text(
                    "ALTER TABLE post ADD COLUMN category VARCHAR(50) NOT NULL DEFAULT 'general'"
                )
            )
            db.session.commit()

    if "user" in tables:
        user_columns = {col["name"] for col in inspector.get_columns("user")}
        alter_statements = []
        if "profile_image_name" not in user_columns:
            alter_statements.append("ALTER TABLE user ADD COLUMN profile_image_name VARCHAR(255) NULL")
        if "required_terms_agreed" not in user_columns:
            alter_statements.append(
                "ALTER TABLE user ADD COLUMN required_terms_agreed BOOLEAN NOT NULL DEFAULT 0"
            )
        if "required_terms_agreed_at" not in user_columns:
            alter_statements.append("ALTER TABLE user ADD COLUMN required_terms_agreed_at DATETIME NULL")
        if "optional_terms_agreed" not in user_columns:
            alter_statements.append(
                "ALTER TABLE user ADD COLUMN optional_terms_agreed BOOLEAN NOT NULL DEFAULT 0"
            )
        if "optional_terms_agreed_at" not in user_columns:
            alter_statements.append("ALTER TABLE user ADD COLUMN optional_terms_agreed_at DATETIME NULL")

        for statement in alter_statements:
            db.session.execute(text(statement))
        if alter_statements:
            db.session.commit()


@app.cli.command("seed-demo")
def seed_demo_cli():
    db.create_all()
    ensure_schema_upgrades()
    admin = ensure_default_admin()
    ensure_provider_subjects(app.config.get("PROVIDER_SEED_SUBJECTS", 100))
    user1 = ensure_user("user1", "user1@example.com", "Hong Gil Dong", "010-1111-1111", "user12345")
    user2 = ensure_user("user2", "user2@example.com", "Kim Min Ji", "010-2222-2222", "user12345")

    post_seed = [
        ("서비스 개선 요청", "medical_service"),
        ("진료 예약 시스템 문의", "digital_service"),
        ("예방접종 대상자 확인 요청", "vaccination"),
    ]
    for title, category in post_seed:
        post = Post.query.filter_by(title=title, user_id=user1.id).first()
        if not post:
            db.session.add(
                Post(
                    title=title,
                    content="데모 데이터로 생성된 게시물입니다.",
                    category=category,
                    user_id=user1.id,
                )
            )
        elif post.category in {None, "", "general"}:
            post.category = category
    db.session.commit()

    notice_data = [
        ("시스템 점검 안내", "이번 주말 시스템 점검이 예정되어 있습니다.", True),
        ("내부 공지", "관리자 전용 비공개 공지입니다.", False),
    ]
    for title, content, is_published in notice_data:
        notice = Notice.query.filter_by(title=title).first()
        if not notice:
            db.session.add(
                Notice(
                    title=title,
                    content=content,
                    is_published=is_published,
                    created_by=admin.id,
                )
            )
    db.session.commit()

    complaint_titles = {"진료비 영수증 문의", "개인정보 열람 요청"}
    for title in complaint_titles:
        complaint = Complaint.query.filter_by(title=title, user_id=user1.id).first()
        if not complaint:
            db.session.add(
                Complaint(
                    title=title,
                    content="데모 데이터로 생성된 민원입니다.",
                    category="general",
                    user_id=user1.id,
                )
            )
    db.session.commit()

    existing_snapshot = (
        MyDataSnapshot.query.filter_by(user_id=user1.id)
        .order_by(MyDataSnapshot.fetched_at.desc(), MyDataSnapshot.id.desc())
        .first()
    )
    if not existing_snapshot:
        payload, _, _ = portal_fetch_mydata_via_provider_api(
            user1,
            client_id=app.config.get("PROVIDER_CLIENT_ID", "portal-client"),
            ttl_seconds=app.config.get("PROVIDER_TOKEN_TTL_SECONDS", 600),
            seed_subjects=app.config.get("PROVIDER_SEED_SUBJECTS", 100),
        )
        db.session.add(
            MyDataSnapshot(
                user_id=user1.id,
                source="PROVIDER_API",
                consent_given=True,
                consent_at=utc_now(),
                payload_json=json.dumps(
                    payload,
                    ensure_ascii=False,
                ),
                fetched_at=utc_now(),
            )
        )
        db.session.commit()

    print("Demo data seeded: admin, user1, user2, posts, notices, complaints, mydata.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        ensure_schema_upgrades()
        ensure_default_admin()
        ensure_provider_subjects(app.config.get("PROVIDER_SEED_SUBJECTS", 100))
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8090")), debug=True)
