from datetime import UTC, datetime

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

    def check_password(self, password):
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
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    actor = db.relationship("User", foreign_keys=[actor_id], lazy=True)


class MyDataSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    source = db.Column(db.String(20), default="MOCK", nullable=False)
    consent_given = db.Column(db.Boolean, default=False, nullable=False)
    consent_at = db.Column(db.DateTime, nullable=True)
    payload_json = db.Column(db.Text, nullable=False)
    fetched_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)


class ProviderSubject(db.Model):
    """
    Mock "MyData Provider" master dataset. This is treated as the external party's storage.

    NOTE: This project is for training/demo, so payload is stored as JSON text for simplicity.
    """

    id = db.Column(db.Integer, primary_key=True)
    subject_ref = db.Column(db.String(32), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(1), nullable=True)  # "M" / "F"
    resident_number = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    payload_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    consents = db.relationship(
        "ProviderConsent",
        backref="subject",
        lazy=True,
        cascade="all, delete-orphan",
    )


class ProviderConsent(db.Model):
    """
    Represents end-user consent/linking between portal user and provider subject record.
    """

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True, unique=True
    )
    provider_subject_id = db.Column(
        db.Integer,
        db.ForeignKey("provider_subject.id"),
        nullable=False,
        index=True,
        unique=True,
    )
    status = db.Column(db.String(20), default="active", nullable=False)  # active / revoked
    consent_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    tokens = db.relationship(
        "ProviderAccessToken",
        backref="consent",
        lazy=True,
        cascade="all, delete-orphan",
    )


class ProviderAccessToken(db.Model):
    """
    Mock OAuth2-like access token issued by the provider.
    """

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    client_id = db.Column(db.String(80), nullable=True)
    consent_id = db.Column(
        db.Integer, db.ForeignKey("provider_consent.id"), nullable=False, index=True
    )
    issued_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)


class PostAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False, index=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False, unique=True)
    mime_type = db.Column(db.String(120), nullable=True)
    file_size = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
