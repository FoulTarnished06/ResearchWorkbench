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
from backend.database import init_db, get_user_by_username, get_user_by_id, create_user

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
        self.assertIn("Incorrect password", login_res_bad.json()["detail"])

        # Unregistered account rejection (404 with explicit warning)
        login_res_unregistered = self.client.post("/api/auth/login", json={
            "username": f"unregistered_user_{unique_suffix}",
            "password": "SomePassword123!"
        })
        self.assertEqual(login_res_unregistered.status_code, 404)
        self.assertIn("not registered", login_res_unregistered.json()["detail"].lower())

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

    def test_07_aes_gcm_authenticated_encryption_and_decryption(self):
        from backend.auth import encrypt_api_key_for_user, decrypt_api_key_for_user
        user_id = f"usr_{uuid.uuid4().hex[:10]}"
        raw_key = "AIzaSySecretGeminiKey123456789"

        encrypted_hex, hint = encrypt_api_key_for_user(raw_key, user_id)
        self.assertIsInstance(encrypted_hex, str)
        self.assertTrue(len(encrypted_hex) > 30)
        self.assertEqual(hint, "...6789")

        # Decrypt with the same user ID returns identical plaintext
        decrypted = decrypt_api_key_for_user(encrypted_hex, user_id)
        self.assertEqual(decrypted, raw_key)

    def test_08_user_cryptographic_isolation_and_tamper_detection(self):
        from backend.auth import encrypt_api_key_for_user, decrypt_api_key_for_user
        user_a = f"usr_a_{uuid.uuid4().hex[:8]}"
        user_b = f"usr_b_{uuid.uuid4().hex[:8]}"
        secret_key = "sk-ant-claude-secret-token-abcdef"

        enc_blob, _ = encrypt_api_key_for_user(secret_key, user_a)

        # Attempting decryption with User B's ID fails due to HKDF salt isolation
        cross_user_decrypt = decrypt_api_key_for_user(enc_blob, user_b)
        self.assertIsNone(cross_user_decrypt, "User B should NEVER be able to decrypt User A's API key!")

        # Tampered ciphertext fails AES-GCM tag verification
        tampered = list(bytes.fromhex(enc_blob))
        tampered[-1] ^= 0x01  # Flip one bit in authentication tag
        tampered_hex = bytes(tampered).hex()
        tamper_result = decrypt_api_key_for_user(tampered_hex, user_a)
        self.assertIsNone(tamper_result, "Tampered ciphertext must fail authentication tag check and return None!")

    def test_09_api_keys_vault_endpoints(self):
        sfx = uuid.uuid4().hex[:6]
        res = self.client.post("/api/auth/register", json={
            "username": f"vault_{sfx}",
            "email": f"vault_{sfx}@lab.edu",
            "password": "Password123!"
        })
        token = res.json()["access_token"]
        auth_hdr = {"Authorization": f"Bearer {token}"}

        # Initial check: no keys configured
        status_res = self.client.get("/api/auth/api-keys", headers=auth_hdr)
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.json()["keys"]
        self.assertFalse(status_data["gemini"]["configured"])
        self.assertFalse(status_data["openai"]["configured"])

        # Store Gemini key
        save_res = self.client.post("/api/auth/api-keys", headers=auth_hdr, json={
            "provider": "gemini",
            "api_key": "AIzaSyGeminiApiKeyTest999"
        })
        self.assertEqual(save_res.status_code, 200)
        save_data = save_res.json()
        self.assertEqual(save_data["status"], "success")
        self.assertEqual(save_data["hint"], "...t999")

        # Verify hint in vault status, ensure NO plaintext returned
        status_res2 = self.client.get("/api/auth/api-keys", headers=auth_hdr)
        status_data2 = status_res2.json()["keys"]
        self.assertTrue(status_data2["gemini"]["configured"])
        self.assertEqual(status_data2["gemini"]["hint"], "...t999")
        self.assertNotIn("AIzaSyGeminiApiKeyTest999", status_res2.text, "Plaintext API key must NEVER be leaked in API response!")

        # Delete key
        del_res = self.client.delete("/api/auth/api-keys/gemini", headers=auth_hdr)
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.json()["deleted"])

        # Verify key is removed
        status_res3 = self.client.get("/api/auth/api-keys", headers=auth_hdr)
        self.assertFalse(status_res3.json()["keys"]["gemini"]["configured"])

    def test_10_oauth_providers_endpoint(self):
        res = self.client.get("/api/auth/providers")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["local"])
        self.assertIn("google", data)
        self.assertIn("github", data)

    def test_11_inject_user_api_keys_helper(self):
        from backend.app import inject_user_api_keys
        from backend.database import save_user_api_key, create_user
        from backend.auth import encrypt_api_key_for_user

        sfx = uuid.uuid4().hex[:8]
        user = create_user(username=f"inj_{sfx}", email=f"inj_{sfx}@test.com", password_hash="dummy_hash")
        user_id = user["id"]
        enc, hint = encrypt_api_key_for_user("stored_openai_key_val", user_id)
        save_user_api_key(user_id, "openai", enc, hint)

        # 1. Config missing key -> automatically injected
        cfg1 = {"query": "Test query"}
        injected_cfg1 = inject_user_api_keys(cfg1, user_id)
        self.assertEqual(injected_cfg1.get("openai_key"), "stored_openai_key_val")

        # 2. Config already has an explicit key -> preserved (does not overwrite)
        cfg2 = {"openai_key": "explicit_key_provided_by_client"}
        injected_cfg2 = inject_user_api_keys(cfg2, user_id)
        self.assertEqual(injected_cfg2.get("openai_key"), "explicit_key_provided_by_client")

        # 3. None user_id -> config unchanged
        cfg3 = {"gemini_key": None}
        injected_cfg3 = inject_user_api_keys(cfg3, None)
        self.assertIsNone(injected_cfg3.get("gemini_key"))

    def test_12_oauth_user_creation_and_account_linking(self):
        from backend.database import create_or_update_oauth_user, get_user_by_oauth

        sfx = uuid.uuid4().hex[:6]
        email = f"oauth_user_{sfx}@gmail.com"
        oauth_id = f"google_sub_{sfx}"

        # Create new user via OAuth
        user1 = create_or_update_oauth_user(
            provider="google",
            oauth_id=oauth_id,
            email=email,
            username=f"GoogleUser_{sfx}",
            avatar_url="https://lh3.googleusercontent.com/test_avatar.jpg"
        )
        self.assertIsNotNone(user1)
        self.assertEqual(user1["email"], email)
        self.assertEqual(user1["oauth_provider"], "google")

        # Find user by provider + oauth_id
        found = get_user_by_oauth("google", oauth_id)
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], user1["id"])

        # Subsequent login updates avatar/last_login without duplicate insertion
        user2 = create_or_update_oauth_user(
            provider="google",
            oauth_id=oauth_id,
            email=email,
            username=f"GoogleUser_{sfx}",
            avatar_url="https://lh3.googleusercontent.com/updated_avatar.jpg"
        )
        self.assertEqual(user2["id"], user1["id"])

    def test_13_login_page_endpoint(self):
        res = self.client.get("/login")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Researcher Access", res.text)
        self.assertIn("Continue with Google", res.text)
        self.assertIn("Continue with GitHub", res.text)
        self.assertIn("Sign In to Workbench", res.text)

    def test_14_root_redirects_unauthenticated_to_login(self):
        """Strictly tests that root (/) redirects unauthenticated users to /login (no guest mode)."""
        anon_client = TestClient(app)
        res = anon_client.get("/", follow_redirects=False)
        self.assertEqual(res.status_code, 303)
        self.assertEqual(res.headers.get("location"), "/login")

        res_index = anon_client.get("/index.html", follow_redirects=False)
        self.assertEqual(res_index.status_code, 303)
        self.assertEqual(res_index.headers.get("location"), "/login")

    def test_15_root_serves_workbench_when_authenticated(self):
        """Tests that authenticated users with valid access_token cookie access the workbench directly."""
        sfx = uuid.uuid4().hex[:6]
        user = create_user(
            username=f"AuthedUser_{sfx}",
            email=f"authed_{sfx}@institution.edu",
            password_hash=hash_password("ValidPassword123!")
        )
        token = create_access_token({"sub": user["id"], "username": user["username"], "role": "user"})
        
        # Test with cookie on clean client
        authed_client = TestClient(app)
        res = authed_client.get("/", cookies={"access_token": token}, follow_redirects=False)
        self.assertEqual(res.status_code, 200)
        self.assertIn("AI Research Workbench", res.text)
        self.assertIn("dock-auth-btn", res.text)

    def test_16_login_page_no_guest_mode(self):
        """Guarantees that the login portal contains no 'Enter as Guest' links."""
        res = self.client.get("/login")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("Enter as Guest", res.text)
        self.assertIn("Workstation Secure Access", res.text)

if __name__ == "__main__":
    unittest.main()

