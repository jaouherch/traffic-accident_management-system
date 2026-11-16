"""Isolated smoke tests; never connect to an existing application database."""

import os
import tempfile
import unittest
from pathlib import Path

from passlib.hash import pbkdf2_sha256

from app import create_app
from db import db
from models.user import User, UserStatus


class ApiSmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="traffic-api-test-")
        os.environ["JWT_SECRET_KEY"] = "test-only-secret-that-is-long-enough-for-tests-12345"
        os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(self.tmpdir.name) / "test.db")
        os.environ.pop("ADMIN_INVITE_CODE", None)
        os.environ.pop("MAIL_USERNAME", None)
        os.environ.pop("MAIL_PASSWORD", None)
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.tmpdir.cleanup()

    def register_and_login(self):
        registered = self.client.post(
            "/register",
            json={"username": "resident", "password": "StrongTest123!", "role": "user"},
        )
        self.assertEqual(registered.status_code, 201, registered.get_json())
        logged_in = self.client.post(
            "/login", json={"username": "resident", "password": "StrongTest123!"}
        )
        self.assertEqual(logged_in.status_code, 200, logged_in.get_json())
        return {"Authorization": "Bearer " + logged_in.get_json()["access_token"]}

    def test_public_routes_and_profile(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        headers = self.register_and_login()
        profile = self.client.get("/profile", headers=headers)
        self.assertEqual(profile.status_code, 200, profile.get_json())
        self.assertEqual(profile.get_json()["status"], "APPROVED")
        self.assertNotIn("password", profile.get_json())

    def test_report_round_trip(self):
        headers = self.register_and_login()
        posted = self.client.post(
            "/accidents",
            data={
                "latitude": "36.8065", "longitude": "10.1815",
                "description": "Collision near an intersection in Tunis.",
                "severity": "3", "casualties_injured": "0", "casualties_dead": "0",
            },
            headers=headers,
        )
        self.assertEqual(posted.status_code, 201, posted.get_json())
        results = self.client.get("/accidents")
        self.assertEqual(results.status_code, 200, results.get_json())
        self.assertEqual(len(results.get_json()), 1)
        self.assertEqual(results.get_json()[0]["status"], "pending_verification")

    def test_admin_registration_disabled_by_default(self):
        request = {
            "username": "candidate", "password": "StrongTest123!",
            "full_name": "Example Person", "department": "Operations",
            "secret_invite_code": "anything",
        }
        response = self.client.post("/register-admin", json=request)
        self.assertEqual(response.status_code, 403, response.get_json())
        with self.app.app_context():
            self.assertEqual(User.query.filter_by(role="admin").count(), 0)

    def test_admin_invite_only_creates_pending_account(self):
        os.environ["ADMIN_INVITE_CODE"] = "local-test-invite-not-a-real-credential"
        response = self.client.post(
            "/register-admin",
            json={
                "username": "candidate", "password": "StrongTest123!",
                "full_name": "Example Person", "department": "Operations",
                "secret_invite_code": "local-test-invite-not-a-real-credential",
            },
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        with self.app.app_context():
            account = User.query.filter_by(username="candidate").one()
            self.assertEqual(account.status, UserStatus.PENDING)

    def test_admin_can_approve_an_officer(self):
        with self.app.app_context():
            admin = User(
                username="testadmin",
                password=pbkdf2_sha256.hash("StrongTest123!"),
                role="admin", status=UserStatus.APPROVED,
            )
            db.session.add(admin)
            db.session.commit()

        logged_in = self.client.post(
            "/login", json={"username": "testadmin", "password": "StrongTest123!"}
        )
        self.assertEqual(logged_in.status_code, 200, logged_in.get_json())
        headers = {"Authorization": "Bearer " + logged_in.get_json()["access_token"]}

        applied = self.client.post(
            "/apply-officer",
            json={
                "username": "candidate", "password": "StrongTest123!",
                "email": "candidate@example.invalid", "institution": "Traffic Office",
                "badge_number": "TEST-001",
            },
        )
        self.assertEqual(applied.status_code, 201, applied.get_json())
        pending = self.client.get("/admin/pending-officers", headers=headers)
        self.assertEqual(pending.status_code, 200, pending.get_json())
        applicants = pending.get_json()["pending_officers"]
        self.assertEqual(len(applicants), 1)
        self.assertEqual(self.client.get("/admin/users", headers=headers).status_code, 200)

        approved = self.client.post(
            "/admin/process-officer",
            json={"user_id": applicants[0]["id"], "action": "approve"},
            headers=headers,
        )
        self.assertEqual(approved.status_code, 200, approved.get_json())
        with self.app.app_context():
            officer = User.query.filter_by(username="candidate").first()
            self.assertEqual(officer.role, "officer")
            self.assertEqual(officer.status, UserStatus.APPROVED)

    def test_invalid_coordinates_are_rejected(self):
        headers = self.register_and_login()
        response = self.client.post(
            "/accidents",
            data={"latitude": "190", "longitude": "10", "description": "Report for unit test.", "severity": "3"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 400, response.get_json())

    def test_old_admin_token_cannot_override_new_database_role(self):
        with self.app.app_context():
            admin = User(
                username="testadmin", password=pbkdf2_sha256.hash("StrongTest123!"),
                role="admin", status=UserStatus.APPROVED,
            )
            db.session.add(admin)
            db.session.commit()

        login = self.client.post(
            "/login", json={"username": "testadmin", "password": "StrongTest123!"}
        )
        headers = {"Authorization": "Bearer " + login.get_json()["access_token"]}
        self.assertEqual(self.client.get("/admin/users", headers=headers).status_code, 200)
        with self.app.app_context():
            User.query.filter_by(username="testadmin").one().role = "user"
            db.session.commit()
        self.assertEqual(self.client.get("/admin/users", headers=headers).status_code, 403)

    def test_comments_allow_only_one_upvote_per_user(self):
        owner_headers = self.register_and_login()
        report = self.client.post(
            "/accidents",
            data={
                "latitude": "36.8", "longitude": "10.2",
                "description": "An accident has blocked the intersection.", "severity": "2",
            },
            headers=owner_headers,
        )
        self.assertEqual(report.status_code, 201, report.get_json())
        accident_id = report.get_json()["id"]
        comment = self.client.post(
            f"/accidents/{accident_id}/comments",
            json={"content": "Please take another route."},
            headers=owner_headers,
        )
        self.assertEqual(comment.status_code, 201, comment.get_json())
        comment_id = comment.get_json()["id"]
        self.assertEqual(
            self.client.post(f"/comments/{comment_id}/upvote", headers=owner_headers).status_code,
            400,
        )

        created = self.client.post(
            "/register", json={"username": "second", "password": "StrongTest123!"}
        )
        self.assertEqual(created.status_code, 201, created.get_json())
        second_login = self.client.post(
            "/login", json={"username": "second", "password": "StrongTest123!"}
        )
        voter_headers = {"Authorization": "Bearer " + second_login.get_json()["access_token"]}
        self.assertEqual(
            self.client.post(f"/comments/{comment_id}/upvote", headers=voter_headers).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(f"/comments/{comment_id}/upvote", headers=voter_headers).status_code,
            409,
        )
        comments = self.client.get(f"/accidents/{accident_id}/comments").get_json()
        self.assertEqual(comments[0]["score"], 1)


if __name__ == "__main__":
    unittest.main()
