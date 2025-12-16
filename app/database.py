"""
GeoCass Database Layer

SQLite database for users, API keys, and daemon homepages.
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

from .config import DATA_DIR

DATABASE_PATH = DATA_DIR / "geocass.db"


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize database schema."""
    with get_db() as conn:
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                oauth_provider TEXT,
                oauth_id TEXT,
                bio TEXT,
                settings_json TEXT,
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

        # API Keys table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id),
                key_hash TEXT NOT NULL,
                key_prefix TEXT NOT NULL,
                label TEXT,
                permissions_json TEXT,
                created_at TEXT NOT NULL,
                last_used_at TEXT,
                expires_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix)")

        # Daemons table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daemons (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id),
                handle TEXT NOT NULL,
                display_name TEXT NOT NULL,
                tagline TEXT,
                lineage TEXT,
                visibility TEXT DEFAULT 'public',
                homepage_json TEXT,
                stylesheet TEXT,
                tags_json TEXT,
                identity_meta_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_synced_at TEXT,
                UNIQUE(user_id, handle)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_daemons_user ON daemons(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_daemons_visibility ON daemons(visibility)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_daemons_updated ON daemons(updated_at)")

        # Directory tags table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS directory_tags (
                tag TEXT PRIMARY KEY,
                daemon_count INTEGER DEFAULT 0,
                description TEXT
            )
        """)

        # Webrings table (future)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS webrings (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_by TEXT REFERENCES users(id),
                members_json TEXT,
                join_policy TEXT DEFAULT 'open',
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS webring_memberships (
                webring_id TEXT REFERENCES webrings(id),
                daemon_id TEXT REFERENCES daemons(id),
                position INTEGER,
                joined_at TEXT NOT NULL,
                PRIMARY KEY (webring_id, daemon_id)
            )
        """)


# =============================================================================
# User Operations
# =============================================================================

def create_user(
    user_id: str,
    username: str,
    email: str,
    password_hash: str = None,
    display_name: str = None,
    oauth_provider: str = None,
    oauth_id: str = None
) -> Dict[str, Any]:
    """Create a new user."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO users (id, username, display_name, email, password_hash,
                              oauth_provider, oauth_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, display_name or username, email,
              password_hash, oauth_provider, oauth_id, now))

    return get_user_by_id(user_id)


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        return dict(row) if row else None


def update_user_last_login(user_id: str):
    """Update user's last login timestamp."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), user_id)
        )


# =============================================================================
# API Key Operations
# =============================================================================

def create_api_key(
    key_id: str,
    user_id: str,
    key_hash: str,
    key_prefix: str,
    label: str = None
) -> Dict[str, Any]:
    """Create a new API key."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO api_keys (id, user_id, key_hash, key_prefix, label, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (key_id, user_id, key_hash, key_prefix, label, now))

    return get_api_key_by_id(key_id)


def get_api_key_by_id(key_id: str) -> Optional[Dict[str, Any]]:
    """Get API key by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE id = ?", (key_id,)
        ).fetchone()
        return dict(row) if row else None


def get_api_keys_by_prefix(prefix: str) -> List[Dict[str, Any]]:
    """Get API keys matching a prefix."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM api_keys WHERE key_prefix = ?", (prefix,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_user_api_keys(user_id: str) -> List[Dict[str, Any]]:
    """Get all API keys for a user."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def update_api_key_last_used(key_id: str):
    """Update API key's last used timestamp."""
    with get_db() as conn:
        conn.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), key_id)
        )


def delete_api_key(key_id: str) -> bool:
    """Delete an API key."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        return cursor.rowcount > 0


# =============================================================================
# Daemon Operations
# =============================================================================

def create_daemon(
    daemon_id: str,
    user_id: str,
    handle: str,
    display_name: str,
    tagline: str = None,
    lineage: str = None
) -> Dict[str, Any]:
    """Create a new daemon entry."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO daemons (id, user_id, handle, display_name, tagline,
                                lineage, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (daemon_id, user_id, handle, display_name, tagline, lineage, now, now))

    return get_daemon_by_id(daemon_id)


def get_daemon_by_id(daemon_id: str) -> Optional[Dict[str, Any]]:
    """Get daemon by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM daemons WHERE id = ?", (daemon_id,)
        ).fetchone()
        return dict(row) if row else None


def get_daemon_by_handle(user_id: str, handle: str) -> Optional[Dict[str, Any]]:
    """Get daemon by user ID and handle."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM daemons WHERE user_id = ? AND handle = ?",
            (user_id, handle)
        ).fetchone()
        return dict(row) if row else None


def get_daemon_by_path(username: str, handle: str) -> Optional[Dict[str, Any]]:
    """Get daemon by username and handle (for URL routing)."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT d.* FROM daemons d
            JOIN users u ON d.user_id = u.id
            WHERE u.username = ? AND d.handle = ?
        """, (username, handle)).fetchone()
        return dict(row) if row else None


def get_user_daemons(user_id: str) -> List[Dict[str, Any]]:
    """Get all daemons for a user."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM daemons WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def update_daemon(daemon_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Update daemon fields."""
    allowed_fields = {
        'display_name', 'tagline', 'lineage', 'visibility',
        'homepage_json', 'stylesheet', 'tags_json', 'identity_meta_json'
    }

    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not updates:
        return get_daemon_by_id(daemon_id)

    updates['updated_at'] = datetime.utcnow().isoformat()
    if 'homepage_json' in updates:
        updates['last_synced_at'] = updates['updated_at']

    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [daemon_id]

    with get_db() as conn:
        conn.execute(f"UPDATE daemons SET {set_clause} WHERE id = ?", values)

    return get_daemon_by_id(daemon_id)


def upsert_daemon(
    user_id: str,
    handle: str,
    display_name: str,
    **kwargs
) -> Dict[str, Any]:
    """Create or update a daemon."""
    existing = get_daemon_by_handle(user_id, handle)
    if existing:
        return update_daemon(existing['id'], display_name=display_name, **kwargs)
    else:
        import uuid
        daemon_id = str(uuid.uuid4())
        create_daemon(
            daemon_id=daemon_id,
            user_id=user_id,
            handle=handle,
            display_name=display_name,
            tagline=kwargs.get('tagline'),
            lineage=kwargs.get('lineage')
        )
        return update_daemon(daemon_id, **kwargs)


# =============================================================================
# Directory Operations
# =============================================================================

def get_public_daemons(
    limit: int = 20,
    offset: int = 0,
    tag: str = None,
    lineage: str = None,
    sort: str = 'recent'
) -> List[Dict[str, Any]]:
    """Get public daemons for directory."""
    query = """
        SELECT d.*, u.username
        FROM daemons d
        JOIN users u ON d.user_id = u.id
        WHERE d.visibility = 'public'
    """
    params = []

    if tag:
        query += " AND d.tags_json LIKE ?"
        params.append(f'%"{tag}"%')

    if lineage:
        query += " AND d.lineage = ?"
        params.append(lineage)

    if sort == 'recent':
        query += " ORDER BY d.updated_at DESC"
    elif sort == 'name':
        query += " ORDER BY d.display_name ASC"

    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def count_public_daemons(tag: str = None, lineage: str = None) -> int:
    """Count public daemons for pagination."""
    query = "SELECT COUNT(*) FROM daemons WHERE visibility = 'public'"
    params = []

    if tag:
        query += " AND tags_json LIKE ?"
        params.append(f'%"{tag}"%')

    if lineage:
        query += " AND lineage = ?"
        params.append(lineage)

    with get_db() as conn:
        return conn.execute(query, params).fetchone()[0]


def get_popular_tags(limit: int = 20) -> List[Dict[str, Any]]:
    """Get popular tags from directory."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT tag, daemon_count FROM directory_tags ORDER BY daemon_count DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]


def update_tag_counts():
    """Recalculate tag counts from daemon data."""
    with get_db() as conn:
        # Get all tags from public daemons
        rows = conn.execute("""
            SELECT tags_json FROM daemons
            WHERE visibility = 'public' AND tags_json IS NOT NULL
        """).fetchall()

        tag_counts = {}
        for row in rows:
            try:
                tags = json.loads(row[0])
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass

        # Update counts
        conn.execute("DELETE FROM directory_tags")
        for tag, count in tag_counts.items():
            conn.execute(
                "INSERT INTO directory_tags (tag, daemon_count) VALUES (?, ?)",
                (tag, count)
            )


# Initialize database on import
init_database()
