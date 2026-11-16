"""Create the first approved admin locally, without a hard-coded password.

Usage: python bootstrap_admin.py --username admin
"""

import argparse
import getpass
import sys

from passlib.hash import pbkdf2_sha256

from app import create_app
from db import db
from models.user import User, UserStatus
from schemas.user import validate_password


def main():
    parser = argparse.ArgumentParser(description="Bootstrap the first admin account")
    parser.add_argument("--username", required=True)
    args = parser.parse_args()

    password = getpass.getpass("Choose a strong admin password: ")
    password_again = getpass.getpass("Repeat password: ")
    if password != password_again:
        sys.exit("Passwords did not match; no user created.")
    if len(password) < 12:
        sys.exit("Use at least 12 characters for the bootstrap password.")
    try:
        validate_password(password)
    except Exception as error:
        sys.exit(f"Password does not meet complexity requirements: {error}")

    app = create_app()
    with app.app_context():
        if User.query.filter_by(role="admin", status=UserStatus.APPROVED).first():
            sys.exit("An approved admin already exists; bootstrap is disabled.")
        if User.query.filter_by(username=args.username).first():
            sys.exit("Username already exists; choose another one.")
        account = User(
            username=args.username,
            password=pbkdf2_sha256.hash(password),
            role="admin",
            status=UserStatus.APPROVED,
        )
        db.session.add(account)
        db.session.commit()
        print("First admin created. You can now sign in through the web interface.")


if __name__ == "__main__":
    main()
