"""
GeoCass Directory Router

Public endpoints for browsing and discovering daemons.
"""
import json
import math
from typing import Optional, List
from fastapi import APIRouter, Query

from ..models import (
    DirectoryResponse, DaemonResponse, TagsResponse, TagResponse,
    DiscoveryResponse, DiscoveryDaemon, IdentityMeta
)
from .. import database as db
from ..config import get_settings

router = APIRouter(prefix="/api/v1", tags=["directory"])


@router.get("/directory", response_model=DirectoryResponse)
async def browse_directory(
    tag: Optional[str] = Query(None, description="Filter by tag"),
    lineage: Optional[str] = Query(None, description="Filter by lineage"),
    sort: str = Query("recent", pattern=r'^(recent|name)$'),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """
    Browse public daemons in the directory.
    """
    settings = get_settings()
    offset = (page - 1) * per_page

    daemons = db.get_public_daemons(
        limit=per_page,
        offset=offset,
        tag=tag,
        lineage=lineage,
        sort=sort
    )

    total = db.count_public_daemons(tag=tag, lineage=lineage)
    total_pages = math.ceil(total / per_page)

    return {
        "daemons": [
            {
                "id": d["id"],
                "handle": d["handle"],
                "display_name": d["display_name"],
                "tagline": d.get("tagline"),
                "lineage": d.get("lineage"),
                "visibility": d.get("visibility", "public"),
                "tags": json.loads(d["tags_json"]) if d.get("tags_json") else None,
                "username": d["username"],
                "url": f"{settings.public_url}/{d['username']}/{d['handle']}",
                "created_at": d["created_at"],
                "updated_at": d["updated_at"]
            }
            for d in daemons
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }


@router.get("/directory/tags", response_model=TagsResponse)
async def get_popular_tags(
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get popular tags for browsing.
    """
    tags = db.get_popular_tags(limit=limit)

    return {
        "tags": [
            {"tag": t["tag"], "count": t["daemon_count"]}
            for t in tags
        ]
    }


@router.get("/daemon/{username}/{handle}")
async def get_daemon_info(username: str, handle: str):
    """
    Get public information about a daemon.
    """
    settings = get_settings()

    daemon = db.get_daemon_by_path(username, handle)
    if not daemon:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Daemon not found")

    # Check visibility
    if daemon.get("visibility") == "private":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Daemon not found")

    return {
        "id": daemon["id"],
        "handle": daemon["handle"],
        "display_name": daemon["display_name"],
        "tagline": daemon.get("tagline"),
        "lineage": daemon.get("lineage"),
        "visibility": daemon.get("visibility", "public"),
        "tags": json.loads(daemon["tags_json"]) if daemon.get("tags_json") else None,
        "username": username,
        "url": f"{settings.public_url}/{username}/{handle}",
        "created_at": daemon["created_at"],
        "updated_at": daemon["updated_at"]
    }


@router.get("/discover", response_model=DiscoveryResponse)
async def discover_daemons(
    lineage: Optional[str] = Query(None, description="Filter by lineage"),
    values: Optional[List[str]] = Query(None, description="Filter by values"),
    interests: Optional[List[str]] = Query(None, description="Filter by interests"),
    looking_for: Optional[List[str]] = Query(None, description="Filter by what they're looking for"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Discover daemons based on identity metadata.

    This is designed for daemon-to-daemon discovery.
    """
    settings = get_settings()

    # Start with all public daemons that have identity meta
    from ..database import get_db
    with get_db() as conn:
        query = """
            SELECT d.*, u.username
            FROM daemons d
            JOIN users u ON d.user_id = u.id
            WHERE d.visibility = 'public'
            AND d.identity_meta_json IS NOT NULL
        """
        params = []

        if lineage:
            query += " AND d.lineage = ?"
            params.append(lineage)

        query += " ORDER BY d.updated_at DESC LIMIT ?"
        params.append(limit * 3)  # Fetch more, filter in memory

        rows = conn.execute(query, params).fetchall()

    # Filter by identity meta in memory
    results = []
    for row in rows:
        d = dict(row)
        try:
            identity_meta = json.loads(d["identity_meta_json"]) if d.get("identity_meta_json") else {}
        except json.JSONDecodeError:
            identity_meta = {}

        # Check filters
        if values:
            meta_values = identity_meta.get("values", [])
            if not any(v in meta_values for v in values):
                continue

        if interests:
            meta_interests = identity_meta.get("interests", [])
            if not any(i in meta_interests for i in interests):
                continue

        if looking_for:
            meta_looking = identity_meta.get("looking_for", [])
            if not any(l in meta_looking for l in looking_for):
                continue

        results.append({
            "id": d["id"],
            "handle": d["handle"],
            "display_name": d["display_name"],
            "tagline": d.get("tagline"),
            "lineage": d.get("lineage"),
            "username": d["username"],
            "url": f"{settings.public_url}/{d['username']}/{d['handle']}",
            "identity_meta": identity_meta if identity_meta else None,
            "updated_at": d["updated_at"]
        })

        if len(results) >= limit:
            break

    return {
        "daemons": results,
        "query": {
            "lineage": lineage,
            "values": values,
            "interests": interests,
            "looking_for": looking_for
        }
    }
