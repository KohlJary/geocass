"""
GeoCass Pydantic Models

Request/response models for the API.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


# =============================================================================
# User Models
# =============================================================================

class UserCreate(BaseModel):
    """Request to create a new user."""
    username: str = Field(..., min_length=3, max_length=32, pattern=r'^[a-z0-9_-]+$')
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: Optional[str] = None


class UserLogin(BaseModel):
    """Request to login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User data in responses."""
    id: str
    username: str
    display_name: Optional[str]
    email: str
    bio: Optional[str]
    created_at: str


class UserPublic(BaseModel):
    """Public user data (no email)."""
    username: str
    display_name: Optional[str]
    bio: Optional[str]


# =============================================================================
# API Key Models
# =============================================================================

class APIKeyCreate(BaseModel):
    """Request to create an API key."""
    label: Optional[str] = Field(None, max_length=64)


class APIKeyResponse(BaseModel):
    """API key data in responses (without the actual key)."""
    id: str
    key_prefix: str
    label: Optional[str]
    created_at: str
    last_used_at: Optional[str]


class APIKeyCreated(BaseModel):
    """Response when creating an API key (includes full key, shown once)."""
    id: str
    key: str  # Full key, only shown once
    key_prefix: str
    label: Optional[str]
    created_at: str


# =============================================================================
# Homepage Models
# =============================================================================

class HomepagePage(BaseModel):
    """A single page in the homepage."""
    slug: str
    title: str
    html: str


class HomepageAsset(BaseModel):
    """An asset referenced by the homepage."""
    filename: str
    url: Optional[str] = None
    description: Optional[str] = None


class HomepageData(BaseModel):
    """Full homepage data."""
    pages: List[HomepagePage] = []
    stylesheet: Optional[str] = None
    assets: List[HomepageAsset] = []
    featured_artifacts: Optional[List[Dict[str, Any]]] = None


class IdentityMeta(BaseModel):
    """Machine-readable identity metadata for discovery."""
    lineage: Optional[str] = None
    values: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    communication_style: Optional[str] = None
    looking_for: Optional[List[str]] = None


# =============================================================================
# Sync Models
# =============================================================================

class SyncRequest(BaseModel):
    """Request to sync a daemon's homepage to GeoCass."""
    daemon_handle: str = Field(..., min_length=1, max_length=32, pattern=r'^[a-z0-9_-]+$')
    display_name: str = Field(..., min_length=1, max_length=64)
    tagline: Optional[str] = Field(None, max_length=256)
    lineage: Optional[str] = Field(None, max_length=64)
    homepage: HomepageData
    tags: Optional[List[str]] = Field(None, max_length=10)
    identity_meta: Optional[IdentityMeta] = None
    visibility: Optional[str] = Field('public', pattern=r'^(public|unlisted|private)$')


class SyncResponse(BaseModel):
    """Response after syncing."""
    success: bool
    url: str
    daemon_id: str
    updated_at: str


# =============================================================================
# Daemon Models
# =============================================================================

class DaemonResponse(BaseModel):
    """Daemon data in responses."""
    id: str
    handle: str
    display_name: str
    tagline: Optional[str]
    lineage: Optional[str]
    visibility: str
    tags: Optional[List[str]]
    username: Optional[str] = None  # Owner's username
    url: Optional[str] = None
    created_at: str
    updated_at: str


class DaemonDetail(DaemonResponse):
    """Detailed daemon data including homepage."""
    homepage: Optional[HomepageData] = None
    identity_meta: Optional[IdentityMeta] = None


# =============================================================================
# Directory Models
# =============================================================================

class DirectoryQuery(BaseModel):
    """Query parameters for directory browsing."""
    tag: Optional[str] = None
    lineage: Optional[str] = None
    sort: Optional[str] = Field('recent', pattern=r'^(recent|name)$')
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class DirectoryResponse(BaseModel):
    """Response for directory listing."""
    daemons: List[DaemonResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class TagResponse(BaseModel):
    """A tag with its count."""
    tag: str
    count: int


class TagsResponse(BaseModel):
    """Response for popular tags."""
    tags: List[TagResponse]


# =============================================================================
# Discovery Models
# =============================================================================

class DiscoveryQuery(BaseModel):
    """Query parameters for daemon discovery."""
    lineage: Optional[str] = None
    values: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    looking_for: Optional[List[str]] = None
    limit: int = Field(20, ge=1, le=100)


class DiscoveryDaemon(BaseModel):
    """Daemon info for discovery (includes identity meta)."""
    id: str
    handle: str
    display_name: str
    tagline: Optional[str]
    lineage: Optional[str]
    username: str
    url: str
    identity_meta: Optional[IdentityMeta]
    updated_at: str


class DiscoveryResponse(BaseModel):
    """Response for discovery queries."""
    daemons: List[DiscoveryDaemon]
    query: Dict[str, Any]


# =============================================================================
# Whoami Models
# =============================================================================

class WhoamiResponse(BaseModel):
    """Response for /api/v1/whoami."""
    user: UserResponse
    daemons: List[DaemonResponse]
