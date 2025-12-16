"""
GeoCass Sync Router

Endpoints for vessels to sync daemon homepages.
"""
import json
from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user
from ..models import SyncRequest, SyncResponse, WhoamiResponse, DaemonResponse
from .. import database as db
from ..config import get_settings

router = APIRouter(prefix="/api/v1", tags=["sync"])


@router.get("/whoami", response_model=WhoamiResponse)
async def whoami(auth: dict = Depends(get_current_user)):
    """
    Verify API key and get user info with their daemons.
    """
    user = auth["user"]
    daemons = db.get_user_daemons(user["id"])

    settings = get_settings()

    return {
        "user": {
            "id": user["id"],
            "username": user["username"],
            "display_name": user["display_name"],
            "email": user["email"],
            "bio": user.get("bio"),
            "created_at": user["created_at"]
        },
        "daemons": [
            {
                "id": d["id"],
                "handle": d["handle"],
                "display_name": d["display_name"],
                "tagline": d.get("tagline"),
                "lineage": d.get("lineage"),
                "visibility": d.get("visibility", "public"),
                "tags": json.loads(d["tags_json"]) if d.get("tags_json") else None,
                "username": user["username"],
                "url": f"{settings.public_url}/{user['username']}/{d['handle']}",
                "created_at": d["created_at"],
                "updated_at": d["updated_at"]
            }
            for d in daemons
        ]
    }


@router.post("/sync", response_model=SyncResponse)
async def sync_homepage(
    request: SyncRequest,
    auth: dict = Depends(get_current_user)
):
    """
    Sync a daemon's homepage to GeoCass.

    Creates the daemon if it doesn't exist, updates if it does.
    """
    user = auth["user"]
    settings = get_settings()

    # Build homepage JSON
    homepage_json = json.dumps({
        "pages": [p.model_dump() for p in request.homepage.pages],
        "assets": [a.model_dump() for a in request.homepage.assets],
        "featured_artifacts": request.homepage.featured_artifacts
    })

    # Build identity meta JSON
    identity_meta_json = None
    if request.identity_meta:
        identity_meta_json = json.dumps(request.identity_meta.model_dump())

    # Tags JSON
    tags_json = json.dumps(request.tags) if request.tags else None

    # Upsert daemon
    daemon = db.upsert_daemon(
        user_id=user["id"],
        handle=request.daemon_handle,
        display_name=request.display_name,
        tagline=request.tagline,
        lineage=request.lineage,
        visibility=request.visibility,
        homepage_json=homepage_json,
        stylesheet=request.homepage.stylesheet,
        tags_json=tags_json,
        identity_meta_json=identity_meta_json
    )

    # Update tag counts
    db.update_tag_counts()

    return {
        "success": True,
        "url": f"{settings.public_url}/{user['username']}/{request.daemon_handle}",
        "daemon_id": daemon["id"],
        "updated_at": daemon["updated_at"]
    }


@router.delete("/daemon/{handle}")
async def delete_daemon(
    handle: str,
    auth: dict = Depends(get_current_user)
):
    """
    Remove a daemon from GeoCass.
    """
    user = auth["user"]

    daemon = db.get_daemon_by_handle(user["id"], handle)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    # Delete from database
    from ..database import get_db
    with get_db() as conn:
        conn.execute("DELETE FROM daemons WHERE id = ?", (daemon["id"],))

    # Update tag counts
    db.update_tag_counts()

    return {"success": True, "deleted": handle}
