import os
import sys
import unittest
import uuid

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from fastapi.testclient import TestClient

from backend.app import app
from backend.auth import (
    hash_password, verify_password, create_access_token, decode_access_token
)
from backend.database import init_db, get_user_by_username, get_user_by_id

class TestAuthenticationSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_01_password_hashing_and_verification(self):
        pwd = "SecretPassword123!"
        hashed = hash_password(pwd)
        self.assertTrue(hashed.startswith("pbkdf2_sha256$100000$"))
        
        # Verify valid password
        self.assertTrue(verify_password(pwd, hashed))
        
        # Verify invalid password
        self.assertFalse(verify_password("WrongPassword!", hashed))
        
        # Salt uniqueness: hashing same password twice produces different hashes
        hashed2 = hash_password(pwd)
        self.assertNotEqual(hashed, hashed2)
        self.assertTrue(verify_password(pwd, hashed2))

    def test_02_jwt_token_creation_and_decoding(self):
        payload = {"sub": "usr_test123", "username": "testuser", "role": "researcher"}
        token = create_access_token(payload)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 20)

        decoded = decode_access_token(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["sub"], "usr_test123")
        self.assertEqual(decoded["username"], "testuser")
        self.assertEqual(decoded["role"], "researcher")

        # Invalid token decoding returns None
        self.assertIsNone(decode_access_token("invalid.token.signature"))

    def test_03_user_registration_endpoint(self):
        unique_suffix = uuid.uuid4().hex[:6]
        username = f"user_{unique_suffix}"
        email = f"user_{unique_suffix}@example.com"
        password = "SecurePassword2026!"

        res = self.client.post("/api/auth/register", json={
            "username": username,
            "email": email,
            "password": password
        })
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["username"], username)
        self.assertEqual(data["user"]["email"], email)

        # Duplicate username rejection
        res_dup_user = self.client.post("/api/auth/register", json={
            "username": username,
            "email": f"diff_{unique_suffix}@example.com",
            "password": password
        })
        self.assertEqual(res_dup_user.status_code, 400)
        self.assertIn("already taken", res_dup_user.json()["detail"])

        # Duplicate email rejection
        res_dup_email = self.client.post("/api/auth/register", json={
            "username": f"diff_{unique_suffix}",
            "email": email,
            "password": password
        })
        self.assertEqual(res_dup_email.status_code, 400)
        self.assertIn("already registered", res_dup_email.json()["detail"])

    def test_04_user_login_endpoint(self):
        unique_suffix = uuid.uuid4().hex[:6]
        username = f"login_{unique_suffix}"
        email = f"login_{unique_suffix}@example.com"
        password = "LoginPass789!"

        # Register first
        reg_res = self.client.post("/api/auth/register", json={
            "username": username,
            "email": email,
            "password": password
        })
        self.assertEqual(reg_res.status_code, 200)

        # Login by username
        login_res1 = self.client.post("/api/auth/login", json={
            "username": username,
            "password": password
        })
        self.assertEqual(login_res1.status_code, 200)
        token1 = login_res1.json()["access_token"]
        self.assertTrue(len(token1) > 20)

        # Login by email
        login_res2 = self.client.post("/api/auth/login", json={
            "username": email,
            "password": password
        })
        self.assertEqual(login_res2.status_code, 200)

        # Wrong password rejection
        login_res_bad = self.client.post("/api/auth/login", json={
            "username": username,
            "password": "WrongPassword!"
        })
        self.assertEqual(login_res_bad.status_code, 401)

    def test_05_auth_me_endpoint_and_logout(self):
        unique_suffix = uuid.uuid4().hex[:6]
        username = f"me_{unique_suffix}"
        email = f"me_{unique_suffix}@example.com"
        password = "MyPassword2026!"

        reg_res = self.client.post("/api/auth/register", json={
            "username": username,
            "email": email,
            "password": password
        })
        token = reg_res.json()["access_token"]

        # Call /api/auth/me with Bearer token
        me_res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)
        me_data = me_res.json()
        self.assertEqual(me_data["username"], username)
        self.assertEqual(me_data["email"], email)

        # Logout endpoint to clear session cookie
        logout_res = self.client.post("/api/auth/logout")
        self.assertEqual(logout_res.status_code, 200)

        # Clear testclient cookies and verify unauthenticated request returns 401
        self.client.cookies.clear()
        unauth_res = self.client.get("/api/auth/me")
        self.assertEqual(unauth_res.status_code, 401)

    def test_06_user_isolated_history_and_sessions(self):
        from backend.database import log_pipeline_run, save_pdf_session
        sfx_a = uuid.uuid4().hex[:6]
        sfx_b = uuid.uuid4().hex[:6]

        # Register User A
        res_a = self.client.post("/api/auth/register", json={
            "username": f"user_a_{sfx_a}",
            "email": f"user_a_{sfx_a}@example.com",
            "password": "PasswordA123!"
        })
        user_a = res_a.json()["user"]
        token_a = res_a.json()["access_token"]

        # Register User B
        res_b = self.client.post("/api/auth/register", json={
            "username": f"user_b_{sfx_b}",
            "email": f"user_b_{sfx_b}@example.com",
            "password": "PasswordB123!"
        })
        user_b = res_b.json()["user"]
        token_b = res_b.json()["access_token"]

        # Clear cookies so tests use explicit Authorization header
        self.client.cookies.clear()

        # Log a run specifically for User A
        run_id_a = f"run_{uuid.uuid4().hex[:8]}"
        log_pipeline_run(
            run_id=run_id_a,
            query="Quantum Computing in User A Workspace",
            tokens_used=500,
            elapsed_seconds=2.5,
            results={"quick_answer": "Summary for User A"},
            prompt_tokens=300,
            completion_tokens=200,
            user_id=user_a["id"]
        )

        # User A checks history -> run_id_a is present
        hist_a = self.client.get("/api/history", headers={"Authorization": f"Bearer {token_a}"}).json()
        run_ids_a = [r["id"] for r in hist_a["runs"]]
        self.assertIn(run_id_a, run_ids_a)

        # User B checks history -> run_id_a is NOT present
        hist_b = self.client.get("/api/history", headers={"Authorization": f"Bearer {token_b}"}).json()
        run_ids_b = [r["id"] for r in hist_b["runs"]]
        self.assertNotIn(run_id_a, run_ids_b)

        # Create a PDF session specifically for User B
        sess_id_b = f"sess_{uuid.uuid4().hex[:8]}"
        save_pdf_session(session_id=sess_id_b, total_files=2, user_id=user_b["id"])

        # User B checks PDF sessions -> sess_id_b is present
        pdf_b = self.client.get("/api/pdf/sessions", headers={"Authorization": f"Bearer {token_b}"}).json()
        sess_ids_b = [s["session_id"] for s in pdf_b["sessions"]]
        self.assertIn(sess_id_b, sess_ids_b)

        # User A checks PDF sessions -> sess_id_b is NOT present
        pdf_a = self.client.get("/api/pdf/sessions", headers={"Authorization": f"Bearer {token_a}"}).json()
        sess_ids_a = [s["session_id"] for s in pdf_a["sessions"]]
        self.assertNotIn(sess_id_b, sess_ids_a)

if __name__ == "__main__":
    unittest.main()

