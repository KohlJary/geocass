"""
GeoCass Authentication

API key authentication for vessel connections.
Password hashing for user accounts.
"""
import secrets
import hashlib
import bcrypt
from typing import Optional, Tuple
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader

from . import database as db
from .config import get_settings

# API Key header
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def generate_api_key() -> Tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, key_hash, key_prefix)
        - full_key: The complete key to give to the user (only shown once)
        - key_hash: Hash to store in database
        - key_prefix: First 8 chars for identification
    """
    settings = get_settings()

    # Generate random key
    random_part = secrets.token_urlsafe(32)
    full_key = f"{settings.api_key_prefix}{random_part}"

    # Hash for storage
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    # Prefix for identification
    key_prefix = full_key[:8]

    return full_key, key_hash, key_prefix


def verify_api_key(api_key: str) -> Optional[str]:
    """
    Verify an API key and return the key ID if valid.

    Args:
        api_key: The full API key

    Returns:
        Key ID if valid, None otherwise
    """
    if not api_key:
        return None

    # Handle "Bearer " prefix
    if api_key.startswith("Bearer "):
        api_key = api_key[7:]

    # Get prefix for lookup
    key_prefix = api_key[:8]

    # Find matching keys
    matching_keys = db.get_api_keys_by_prefix(key_prefix)
    if not matching_keys:
        return None

    # Verify against hash
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    for key_record in matching_keys:
        if key_record['key_hash'] == key_hash:
            # Check expiration
            if key_record.get('expires_at'):
                from datetime import datetime
                if datetime.fromisoformat(key_record['expires_at']) < datetime.utcnow():
                    return None

            # Update last used
            db.update_api_key_last_used(key_record['id'])
            return key_record['id']

    return None


async def get_current_user(
    authorization: str = Security(api_key_header)
) -> dict:
    """
    FastAPI dependency to get the current user from API key.

    Raises HTTPException if authentication fails.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )

    key_id = verify_api_key(authorization)
    if not key_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    # Get key record
    key_record = db.get_api_key_by_id(key_id)
    if not key_record:
        raise HTTPException(
            status_code=401,
            detail="API key not found"
        )

    # Get user
    user = db.get_user_by_id(key_record['user_id'])
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return {
        "user": user,
        "api_key": key_record
    }


async def get_optional_user(
    authorization: str = Security(api_key_header)
) -> Optional[dict]:
    """
    FastAPI dependency to optionally get the current user.

    Returns None if no valid authentication, doesn't raise.
    """
    if not authorization:
        return None

    key_id = verify_api_key(authorization)
    if not key_id:
        return None

    key_record = db.get_api_key_by_id(key_id)
    if not key_record:
        return None

    user = db.get_user_by_id(key_record['user_id'])
    if not user:
        return None

    return {
        "user": user,
        "api_key": key_record
    }
