"""Authentication, account registration, and administrative approval routes."""

import hmac
import os
import smtplib
import ssl
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from flask import current_app, request
from flask.views import MethodView
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from flask_smorest import Blueprint, abort
from passlib.hash import pbkdf2_sha256

from blocklist import blocklist
from db import db
from decorators import admin_required
from models.user import User, UserStatus
from schemas.user import (
    AdminApplicationSchema,
    LoginSchema,
    OfficerApplicationSchema,
    TokenResponseSchema,
    UserSchema,
)

blp = Blueprint("auth", __name__, description="Authentication and approvals")


def send_approval_email(user):
    """Send optional admin approval notification; never keep mail credentials in code."""
    sender = os.getenv("MAIL_USERNAME", "").strip()
    password = os.getenv("MAIL_PASSWORD", "").strip()
    recipient = os.getenv("ADMIN_NOTIFICATION_EMAIL", "").strip()
    if not (sender and password and recipient):
        current_app.logger.info("Admin notification email not configured; request remains pending")
        return False

    message = MIMEText(
        f"A new administrator is awaiting approval.\n"
        f"Username: {user.username}\n"
        f"User ID: {user.id}\n"
        "Use the authenticated /admin/process-admin endpoint to review the request.",
        "plain",
        "utf-8",
    )
    message["Subject"] = "Traffic Accident API: administrator approval requested"
    message["From"] = sender
    message["To"] = recipient

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(sender, password)
            server.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        current_app.logger.exception("Could not send admin approval notification")
        return False


@blp.route("/register")
class Register(MethodView):
    @blp.arguments(UserSchema)
    def post(self, user_data):
        raw_data = request.get_json(silent=True) or {}
        requested_role = str(raw_data.get("role", "user")).lower()
        if requested_role == "admin":
            abort(403, message="Administrator registration uses /register-admin.")
        if requested_role == "officer":
            abort(400, message="Officers must use /apply-officer.")
        if User.query.filter_by(username=user_data["username"]).first():
            abort(400, message="User already exists.")

        user = User(
            username=user_data["username"],
            password=pbkdf2_sha256.hash(user_data["password"]),
            email=user_data.get("email"),
            role="user",
            status=UserStatus.APPROVED,
        )
        db.session.add(user)
        db.session.commit()
        return {"message": "Registration successful.", "username": user.username, "role": user.role}, 201


@blp.route("/login")
class Login(MethodView):
    @blp.arguments(LoginSchema)
    @blp.response(200, TokenResponseSchema)
    def post(self, user_data):
        user = User.query.filter_by(username=user_data["username"]).first()
        if user is None or not pbkdf2_sha256.verify(user_data["password"], user.password):
            abort(401, message="Invalid username or password.")

        if user.status == UserStatus.PENDING:
            abort(403, message="Account is still pending approval.")
        if user.status != UserStatus.APPROVED:
            abort(403, message="Your application was rejected.")
        if user.banned_until and user.banned_until > datetime.utcnow():
            abort(403, message="Account is temporarily or permanently banned.")

        return {
            "access_token": create_access_token(identity=str(user.id), fresh=True),
            "refresh_token": create_refresh_token(identity=str(user.id)),
            "role": user.role,
            "username": user.username,
        }, 200


@blp.route("/logout")
class UserLogout(MethodView):
    @jwt_required()
    def post(self):
        blocklist.add(get_jwt()["jti"])
        return {"message": "Successfully logged out"}, 200


@blp.route("/refresh")
class TokenRefresh(MethodView):
    @jwt_required(refresh=True)
    def post(self):
        token = create_access_token(identity=get_jwt_identity(), fresh=False)
        return {"access_token": token}, 200


@blp.route("/apply-officer")
class OfficerApplication(MethodView):
    @blp.arguments(OfficerApplicationSchema)
    def post(self, officer_data):
        if User.query.filter_by(username=officer_data["username"]).first():
            abort(400, message="Username already exists.")
        user = User(
            username=officer_data["username"],
            password=pbkdf2_sha256.hash(officer_data["password"]),
            email=officer_data["email"],
            institution=officer_data["institution"],
            badge_number=officer_data["badge_number"],
            role="user",
            status=UserStatus.PENDING,
        )
        db.session.add(user)
        db.session.commit()
        return {"message": "Application submitted. Awaiting admin approval."}, 201


@blp.route("/register-admin")
class AdminRegister(MethodView):
    @blp.arguments(AdminApplicationSchema)
    def post(self, admin_data):
        configured_invite = os.getenv("ADMIN_INVITE_CODE", "")
        candidate = admin_data.get("secret_invite_code", "")
        if not configured_invite or not hmac.compare_digest(candidate, configured_invite):
            abort(403, message="Administrator registration is disabled or invite is invalid.")
        if User.query.filter_by(username=admin_data["username"]).first():
            abort(400, message="Username already exists.")

        user = User(
            username=admin_data["username"],
            password=pbkdf2_sha256.hash(admin_data["password"]),
            role="admin",
            status=UserStatus.PENDING,
            full_name=admin_data.get("full_name"),
            department=admin_data.get("department"),
        )
        db.session.add(user)
        db.session.commit()
        send_approval_email(user)
        return {"message": "Admin registration submitted; awaiting existing admin approval."}, 201


@blp.route("/admin/users/<string:user_id>")
class AdminUserDelete(MethodView):
    @jwt_required()
    @admin_required
    def delete(self, user_id):
        if str(user_id) == get_jwt_identity():
            abort(400, message="You cannot delete your own account.")
        user = User.query.get_or_404(user_id)
        if user.role == "admin":
            abort(403, message="Administrative accounts cannot be deleted here.")
        db.session.delete(user)
        db.session.commit()
        return {"message": "User deleted successfully."}, 200


@blp.route("/admin/pending-officers")
class PendingOfficers(MethodView):
    @jwt_required()
    @admin_required
    def get(self):
        users = User.query.filter_by(status=UserStatus.PENDING, role="user").all()
        return {"pending_officers": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "institution": user.institution,
                "badge_number": user.badge_number,
                "role_requested": "officer",
            }
            for user in users
        ]}, 200


@blp.route("/admin/pending-admins")
class PendingAdmins(MethodView):
    @jwt_required()
    @admin_required
    def get(self):
        users = User.query.filter_by(status=UserStatus.PENDING, role="admin").all()
        return {"pending_admins": [
            {"id": user.id, "username": user.username, "full_name": user.full_name}
            for user in users
        ]}, 200


@blp.route("/admin/process-admin")
class ProcessAdmin(MethodView):
    @jwt_required()
    @admin_required
    def post(self):
        data = request.get_json(silent=True) or {}
        user = User.query.get_or_404(data.get("user_id"))
        if user.role != "admin" or user.status != UserStatus.PENDING:
            abort(400, message="Target must be a pending administrator.")
        if data.get("action") == "approve":
            user.status = UserStatus.APPROVED
            db.session.commit()
            return {"message": "Admin account approved."}, 200
        if data.get("action") == "reject":
            user.status = UserStatus.REJECTED
            db.session.commit()
            return {"message": "Admin request rejected."}, 200
        abort(400, message="Invalid action.")


@blp.route("/admin/process-officer")
class ProcessOfficer(MethodView):
    @jwt_required()
    @admin_required
    def post(self):
        data = request.get_json(silent=True) or {}
        user = User.query.get_or_404(data.get("user_id"))
        if user.role != "user" or user.status != UserStatus.PENDING:
            abort(400, message="Target must be a pending officer applicant.")
        if data.get("action") == "approve":
            user.status = UserStatus.APPROVED
            user.role = "officer"
            message = "Approved as officer."
        elif data.get("action") == "reject":
            user.status = UserStatus.REJECTED
            message = "Application rejected."
        else:
            abort(400, message="Invalid action.")
        db.session.commit()
        return {"message": message}, 200


@blp.route("/admin/users/<string:user_id>/ban")
class BanUser(MethodView):
    @jwt_required()
    @admin_required
    def post(self, user_id):
        user = User.query.get_or_404(user_id)
        if user.role == "admin":
            abort(400, message="You cannot ban an administrator.")
        action = (request.get_json(silent=True) or {}).get("duration")
        now = datetime.utcnow()
        durations = {
            "1day": now + timedelta(days=1),
            "1week": now + timedelta(weeks=1),
            "permanent": datetime.max,
            "unban": None,
        }
        if action not in durations:
            abort(400, message="Invalid duration.")
        user.banned_until = durations[action]
        db.session.commit()
        return {"message": "Ban status updated."}, 200
