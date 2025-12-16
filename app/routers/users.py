"""
GeoCass Users Router

User registration, login, and API key management.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user, hash_password, verify_password, generate_api_key
from ..models import (
    UserCreate, UserLogin, UserResponse,
    APIKeyCreate, APIKeyResponse, APIKeyCreated
)
from .. import database as db

router = APIRouter(prefix="/api/v1", tags=["users"])


@router.post("/register", response_model=UserResponse)
async def register(request: UserCreate):
    """
    Register a new user account.
    """
    # Check if username is taken
    if db.get_user_by_username(request.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    # Check if email is taken
    if db.get_user_by_email(request.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user_id = str(uuid.uuid4())
    password_hash = hash_password(request.password)

    user = db.create_user(
        user_id=user_id,
        username=request.username,
        email=request.email,
        password_hash=password_hash,
        display_name=request.display_name
    )

    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "email": user["email"],
        "bio": user.get("bio"),
        "created_at": user["created_at"]
    }


@router.post("/login")
async def login(request: UserLogin):
    """
    Login and get user info + first API key.

    Returns an API key on successful login for bootstrapping.
    """
    user = db.get_user_by_email(request.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Account uses OAuth login")

    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Update last login
    db.update_user_last_login(user["id"])

    # Generate an API key for this session
    full_key, key_hash, key_prefix = generate_api_key()
    key_id = str(uuid.uuid4())
    key_record = db.create_api_key(
        key_id=key_id,
        user_id=user["id"],
        key_hash=key_hash,
        key_prefix=key_prefix,
        label="Login session"
    )

    return {
        "success": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "display_name": user["display_name"],
            "email": user["email"]
        },
        "api_key": full_key  # Only shown once!
    }


@router.post("/keys", response_model=APIKeyCreated)
async def create_api_key(
    request: APIKeyCreate,
    auth: dict = Depends(get_current_user)
):
    """
    Create a new API key.

    The full key is only returned once - store it securely!
    """
    user = auth["user"]

    # Generate key
    full_key, key_hash, key_prefix = generate_api_key()

    # Store in database
    key_id = str(uuid.uuid4())
    key_record = db.create_api_key(
        key_id=key_id,
        user_id=user["id"],
        key_hash=key_hash,
        key_prefix=key_prefix,
        label=request.label
    )

    return {
        "id": key_record["id"],
        "key": full_key,  # Only shown once!
        "key_prefix": key_prefix,
        "label": request.label,
        "created_at": key_record["created_at"]
    }


@router.get("/keys", response_model=list[APIKeyResponse])
async def list_api_keys(auth: dict = Depends(get_current_user)):
    """
    List all API keys for the current user.
    """
    user = auth["user"]
    keys = db.get_user_api_keys(user["id"])

    return [
        {
            "id": k["id"],
            "key_prefix": k["key_prefix"],
            "label": k.get("label"),
            "created_at": k["created_at"],
            "last_used_at": k.get("last_used_at")
        }
        for k in keys
    ]


@router.delete("/keys/{key_id}")
async def delete_api_key(
    key_id: str,
    auth: dict = Depends(get_current_user)
):
    """
    Delete an API key.
    """
    user = auth["user"]

    # Verify the key belongs to the user
    key = db.get_api_key_by_id(key_id)
    if not key or key["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="API key not found")

    # Don't allow deleting the current key
    if key["id"] == auth["api_key"]["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete the API key you're currently using")

    db.delete_api_key(key_id)

    return {"success": True, "deleted": key_id}
