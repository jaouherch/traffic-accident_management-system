"""Flask application factory for the Traffic Accident Management System."""

import os
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_smorest import Api

from blocklist import blocklist
from db import db
from models import user  # noqa: F401 - registers the SQLAlchemy model
from models.accident import Accident  # noqa: F401
from models.comment import Comment  # noqa: F401
from models.route import Route  # noqa: F401
from models.user import User, UserStatus
from resources.accident import blp as AccidentBlueprint
from resources.auth import blp as AuthBlueprint
from resources.comment import blp as CommentBlueprint
from resources.navigation import blp as NavBlueprint
from resources.user import blp as UserBlueprint


def create_app():
    load_dotenv(Path(__file__).with_name(".env"))

    secret = os.getenv("JWT_SECRET_KEY", "").strip()
    if len(secret) < 32 or secret.startswith("REPLACE_WITH_"):
        raise RuntimeError(
            "JWT_SECRET_KEY is missing or too short. Set a random secret "
            "of at least 32 characters in backend/.env."
        )

    app = Flask(__name__)
    allowed_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]
    CORS(app, origins=allowed_origins)

    app.config.update(
        API_TITLE="Traffic Accident API",
        API_VERSION="v1",
        OPENAPI_VERSION="3.0.3",
        OPENAPI_URL_PREFIX="/",
        OPENAPI_SWAGGER_UI_PATH="/swagger-ui",
        OPENAPI_SWAGGER_UI_URL="https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///data.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=secret,
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    )

    db.init_app(app)
    jwt = JWTManager(app)
    api = Api(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_in_blocklist(jwt_header, jwt_payload):
        return jwt_payload["jti"] in blocklist

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return {"message": "The token has been revoked.", "error": "token_revoked"}, 401

    @jwt.additional_claims_loader
    def add_claims_to_jwt(identity):
        current_user = db.session.get(User, identity)
        role = current_user.role if current_user else "user"
        return {
            "is_admin": role == "admin",
            "is_officer": role == "officer",
            "role": role,
        }

    @jwt.user_lookup_loader
    def user_lookup_callback(jwt_header, jwt_data):
        current_user = db.session.get(User, jwt_data["sub"])
        if current_user is None or current_user.status != UserStatus.APPROVED:
            return None
        if current_user.banned_until and current_user.banned_until > datetime.utcnow():
            return None
        return current_user

    api.register_blueprint(AuthBlueprint)
    api.register_blueprint(AccidentBlueprint)
    api.register_blueprint(CommentBlueprint)
    api.register_blueprint(UserBlueprint)
    api.register_blueprint(NavBlueprint)

    with app.app_context():
        db.create_all()

    @app.route("/")
    def home():
        return {"status": "online", "message": "API Running", "swagger": "/swagger-ui"}

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(
        debug=os.getenv("FLASK_DEBUG") == "1",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
    )
