"""
Authentication module for Meridian API.
Handles JWT token creation/verification and password hashing/validation.
"""

import json
import base64
import hashlib
import hmac
import time

from config import JWT_SECRET


# ============================================================
# SIMPLE JWT (HMAC-SHA256)
# ============================================================
def create_token(user_id):
    """Create a JWT token for the given user_id."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
    payload = base64.urlsafe_b64encode(json.dumps({"userId": user_id, "exp": int(time.time()) + 7 * 86400}).encode()).decode().rstrip('=')
    sig = hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    signature = base64.urlsafe_b64encode(sig).decode().rstrip('=')
    return f"{header}.{payload}.{signature}"


def verify_token(token):
    """Verify a JWT token and return the user_id if valid, None otherwise."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header, payload, signature = parts
        expected_sig = hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        expected = base64.urlsafe_b64encode(expected_sig).decode().rstrip('=')
        if not hmac.compare_digest(signature, expected):
            return None
        # Pad base64
        padded = payload + '=' * (4 - len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        if data.get('exp', 0) < time.time():
            return None
        return data.get('userId')
    except Exception:
        return None


# ============================================================
# PASSWORD HASHING
# ============================================================
def hash_password(password):
    """Hash a password using PBKDF2-SHA256 with a random salt."""
    import os
    salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return f"{salt}:{h}"


def check_password(password, stored):
    """Check if a password matches a stored hash."""
    salt, h = stored.split(':')
    return hmac.compare_digest(
        hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex(),
        h
    )
