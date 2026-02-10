from datetime import UTC, datetime
import hashlib

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # A02: 평문 비밀번호 저장 취약점 추가
    password_plain = db.Column(db.String(255), nullable=True)

    profile_image_name = db.Column(db.String(255), nullable=True)
    required_terms_agreed = db.Column(db.Boolean, default=False, nullable=False)
    required_terms_agreed_at = db.Column(db.DateTime, nullable=True)
    optional_terms_agreed = db.Column(db.Boolean, default=False, nullable=False)
    optional_terms_agreed_at = db.Column(db.DateTime, nullable=True)

    role = db.Column(db.String(20), default="user", nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    posts = db.relationship("Post", backref="author", lazy=True)
    complaints = db.relationship(
        "Complaint",
        foreign_keys="Complaint.user_id",
        backref="requester",
        lazy=True,
    )
    assigned_complaints = db.relationship(
        "Complaint",
        foreign_keys="Complaint.assigned_admin_id",
        backref="assigned_admin",
        lazy=True,
    )
    mydata_snapshots = db.relationship(
        "MyDataSnapshot",
        backref="owner",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        # A02 취약점: 평문 비밀번호 저장
        self.password_plain = password

    def check_password(self, password):
        # A02 취약점: 평문 비교도 가능하도록 함
        if self.password_plain == password:
            return True
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default="general", nullable=False)
    status = db.Column(db.String(20), default="open", nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    attachments = db.relationship(
        "PostAttachment",
        backref="post",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(30), default="received", nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    assigned_admin_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(200), nullable=False)
    target_type = db.Column(db.String(50), nullable=True)
    target_id = db.Column(db.String(50), nullable=True)
    meta = db.Column(db.Text, nullable=True)
    # A09 취약점: 민감한 정보 로깅
    sensitive_data = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    actor = db.relationship("User", foreign_keys=[actor_id], lazy=True)


class MyDataSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    source = db.Column(db.String(20), default="MOCK", nullable=False)
    consent_given = db.Column(db.Boolean, default=False, nullable=False)
    consent_at = db.Column(db.DateTime, nullable=True)
    # A02 취약점: 의료정보 암호화 미적용
    payload_json = db.Column(db.Text, nullable=False)
    fetched_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)


class PostAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False, index=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False, unique=True)
    mime_type = db.Column(db.String(120), nullable=True)
    file_size = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
