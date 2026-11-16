"""User profiles, leaderboard and administrator user management."""

from flask import request
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from db import db
from decorators import admin_required
from models.user import User, UserStatus
from schemas.user import LeaderboardUserSchema, UserSchema

blp = Blueprint("Users", __name__, description="Operations on users")


@blp.route("/profile")
class UserProfile(MethodView):
    @jwt_required()
    @blp.response(200, UserSchema)
    def get(self):
        return User.query.get_or_404(get_jwt_identity())


@blp.route("/leaderboard")
class Leaderboard(MethodView):
    @blp.response(200, LeaderboardUserSchema(many=True))
    def get(self):
        users = User.query.order_by(User.points.desc()).limit(10).all()
        for rank, account in enumerate(users, 1):
            account.rank = rank
        return users


@blp.route("/admin/users")
class AdminUserList(MethodView):
    @jwt_required()
    @admin_required
    @blp.response(200, UserSchema(many=True))
    def get(self):
        return User.query.all()


@blp.route("/admin/users/<string:user_id>/status")
class AdminUserStatus(MethodView):
    @jwt_required()
    @admin_required
    def put(self, user_id):
        account = User.query.get_or_404(user_id)
        if account.role == "admin":
            abort(403, message="Administrator status is managed separately.")
        action = (request.get_json(silent=True) or {}).get("status")
        if action == "approved":
            account.status = UserStatus.APPROVED
        elif action == "rejected":
            account.status = UserStatus.REJECTED
        else:
            abort(400, message="Invalid status. Use 'approved' or 'rejected'.")
        db.session.commit()
        return {"message": f"User account {action}."}, 200
