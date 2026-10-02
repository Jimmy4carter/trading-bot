"""
Security & Authentication Layer.
Provides robust password verification and JWT token issuing for the Admin Dashboard.
"""

import time
import hashlib
import hmac
import logging
from typing import Optional, Dict, Any

from config.settings import settings

logger = logging.getLogger("trading_bot.security")

# Helper for secure constant-time password check
def verify_password(plain_password: str, hashed_or_plain: str) -> bool:
    """Verifies plain password against stored hash or configured password."""
    # Direct constant-time string match
    if hmac.compare_digest(plain_password, hashed_or_plain):
        return True
    
    # SHA256 hashed match
    hashed_input = hashlib.sha256(plain_password.encode()).hexdigest()
    if hmac.compare_digest(hashed_input, hashed_or_plain):
        return True

    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(plain_password, hashed_or_plain)
    except Exception:
        return False

def hash_password(password: str) -> str:
    """Hashes a password with SHA-256 (or bcrypt if available)."""
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)
    except Exception:
        return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: Dict[str, Any], expires_delta_seconds: Optional[int] = None) -> str:
    """Generates a signed JWT token."""
    to_encode = data.copy()
    expire_timestamp = time.time() + (expires_delta_seconds or (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60))
    to_encode.update({"exp": expire_timestamp})

    try:
        from jose import jwt
        return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    except ImportError:
        # Fallback pure-Python JWT-like token (header.payload.signature)
        import base64
        import json
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).decode().rstrip("=")
        signing_input = f"{header}.{payload}"
        signature = hmac.new(settings.JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256).digest()
        sig_encoded = base64.urlsafe_b64encode(signature).decode().rstrip("=")
        return f"{header}.{payload}.{sig_encoded}"

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verifies and decodes a signed JWT token."""
    try:
        from jose import jwt, JWTError
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except ImportError:
        # Fallback verification
        import base64
        import json
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header, payload, sig = parts
            signing_input = f"{header}.{payload}"
            expected_sig = hmac.new(settings.JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256).digest()
            sig_encoded = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
            if not hmac.compare_digest(sig, sig_encoded):
                return None
            
            # Decode payload
            payload_padded = payload + "=" * (-len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(payload_padded).decode())
            if data.get("exp", 0) < time.time():
                return None
            return data
        except Exception as e:
            logger.error(f"Fallback token verification failed: {e}")
            return None
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        return None
