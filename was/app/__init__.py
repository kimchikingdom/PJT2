import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "로그인이 필요합니다."


def create_app(config_override=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "sqlite:///local_dev.db"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
        POST_UPLOAD_DIR=os.environ.get(
            "POST_UPLOAD_DIR",
            os.path.join(os.path.dirname(__file__), "static", "uploads", "posts"),
        ),
        PROFILE_UPLOAD_DIR=os.environ.get(
            "PROFILE_UPLOAD_DIR",
            os.path.join(os.path.dirname(__file__), "static", "uploads", "profiles"),
        ),
    )

    if config_override:
        app.config.update(config_override)

    os.makedirs(app.config["POST_UPLOAD_DIR"], exist_ok=True)
    os.makedirs(app.config["PROFILE_UPLOAD_DIR"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app import routes

    routes.init_routes(app)

    with app.app_context():
        from app import models

    return app
