"""Current-account role checks for protected routes.

Authorization must consult the database, not role claims from an old JWT.
"""

from functools import wraps

from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_smorest import abort

from db import db
from models.user import User, UserStatus


def _role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            account = db.session.get(User, get_jwt_identity())
            if account is None or account.status != UserStatus.APPROVED:
                abort(403, message="Account is not active.")
            if account.role not in allowed_roles:
                abort(403, message="Insufficient privileges.")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


admin_required = _role_required("admin")
officer_required = _role_required("officer", "admin")
