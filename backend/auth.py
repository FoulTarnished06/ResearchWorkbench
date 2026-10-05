import os
import re
import secrets
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import jwt
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, field_validator
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from backend.logger import logger

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# ==============================================================================
# Authenticated AES-256-GCM Key Vault Encryption (Per-User Isolation)
# ==============================================================================

def _derive_user_encryption_key(user_id: str) -> bytes:
    """
    Derives a cryptographically strong 256-bit AES key unique to this user.
    Uses HKDF-SHA256 with the master server secret and user_id as salt.
    """
    master = get_jwt_secret().encode("utf-8")
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=user_id.encode("utf-8"),
        info=b"researchworkbench-user-api-key-vault-v1"
    )
    return hkdf.derive(master)

def encrypt_api_key_for_user(api_key: str, user_id: str) -> Tuple[str, str]:
    """
    Encrypts an API key using AES-256-GCM with a fresh 96-bit cryptographic nonce.
    Returns: (encrypted_hex_blob, masked_hint)
    """
    clean_key = api_key.strip()
    if not clean_key:
        raise ValueError("API key cannot be empty.")
    
    key = _derive_user_encryption_key(user_id)
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)  # Standard 96-bit nonce
    ciphertext = aesgcm.encrypt(nonce, clean_key.encode("utf-8"), None)
    
    # Pack nonce (12 bytes) + ciphertext/tag into a single hex string
    encrypted_blob = (nonce + ciphertext).hex()
    
    # Generate a safe masked hint (e.g. "...x7Y9") without revealing the key
    hint = f"...{clean_key[-4:]}" if len(clean_key) >= 6 else "••••••••"
    return encrypted_blob, hint

def decrypt_api_key_for_user(encrypted_blob: str, user_id: str) -> Optional[str]:
    """
    Decrypts an AES-256-GCM encrypted API key in-memory for authorized pipeline execution.
    Tampered ciphertexts or wrong user keys will raise InvalidTag and return None.
    """
    if not encrypted_blob:
        return None
    try:
        raw = bytes.fromhex(encrypted_blob)
        if len(raw) < 28:  # 12 nonce + 16 auth tag minimum
            return None
        nonce, ciphertext = raw[:12], raw[12:]
        key = _derive_user_encryption_key(user_id)
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted.decode("utf-8")
    except Exception as e:
        logger.error(f"Decryption failed for user {user_id}: {e}")
        return None

def get_jwt_secret() -> str:
    """Retrieves the JWT signing secret from env or a persistent secret file."""
    secret = os.getenv("JWT_SECRET")
    if secret and len(secret.strip()) >= 16:
        return secret.strip()
    
    secret_file = Path(__file__).resolve().parent / ".jwt_secret"
    try:
        if secret_file.exists():
            val = secret_file.read_text(encoding="utf-8").strip()
            if val:
                return val
        new_secret = secrets.token_urlsafe(32)
        secret_file.write_text(new_secret, encoding="utf-8")
        return new_secret
    except Exception as e:
        logger.warning(f"Failed to access .jwt_secret file: {e}")
        return "researchworkbench-fallback-dev-secret-key-32bytes-min"

def hash_password(password: str) -> str:
    """Generates a secure PBKDF2-HMAC-SHA256 password hash with 100,000 iterations and a unique salt."""
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    ).hex()
    return f"pbkdf2_sha256$100000${salt}${derived}"

def verify_password(password: str, hashed: str) -> bool:
    """Verifies a plaintext password against the stored PBKDF2 hash using constant-time comparison."""
    try:
        parts = hashed.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected_hash = parts[3]
        computed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations
        ).hex()
        return hmac.compare_digest(computed, expected_hash)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generates an encoded JWT signed with HMAC-SHA256."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, get_jwt_secret(), algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token signature and expiration."""
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None

# Pydantic Schemas
class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        clean = v.strip()
        if not re.match(r"^[a-zA-Z0-9_\-]+$", clean):
            raise ValueError("Username may only contain letters, numbers, underscores, and hyphens.")
        return clean

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError("Invalid email format.")
        return clean

class UserLoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str = "user"
    oauth_provider: str = "local"
    avatar_url: Optional[str] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class SaveApiKeyRequest(BaseModel):
    provider: str = Field(..., pattern="^(gemini|anthropic|openai|serpapi)$")
    api_key: str = Field(..., min_length=4, max_length=512)

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, v: str) -> str:
        return v.strip().lower()

class ApiKeyItem(BaseModel):
    is_set: bool
    configured: bool = False
    hint: Optional[str] = None
    updated_at: Optional[str] = None

class ApiKeysStatusResponse(BaseModel):
    status: str = "success"
    keys: Dict[str, ApiKeyItem]

class OAuthProvidersResponse(BaseModel):
    local: bool = True
    google: bool
    github: bool

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_current_user_optional(
    request: Request,
    bearer_token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[Dict[str, Any]]:
    """Dependency that returns the authenticated user if valid token is provided, or None for anonymous."""
    token = bearer_token
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
    if not token:
        token = request.cookies.get("access_token") or request.cookies.get("workbench_token")
    
    if not token:
        return None
    
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    
    user_id = payload["sub"]
    from backend.database import get_user_by_id
    user = get_user_by_id(user_id)
    return user

async def get_current_user_required(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """Dependency requiring active authentication; returns 401 if unauthenticated."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in to access this resource.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user
