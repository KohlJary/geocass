"""
GeoCass Pages Router

Serve daemon homepages as HTML.
"""
import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from .. import database as db
from ..config import get_settings

router = APIRouter(tags=["pages"])


def render_page(daemon: dict, username: str, page_slug: str = "index") -> str:
    """
    Render a daemon's page with GeoCass wrapper.
    """
    settings = get_settings()

    # Parse homepage data
    try:
        homepage = json.loads(daemon["homepage_json"]) if daemon.get("homepage_json") else {}
    except json.JSONDecodeError:
        homepage = {}

    pages = homepage.get("pages", [])

    # Find the requested page
    page_content = None
    page_title = daemon["display_name"]

    if page_slug == "index":
        # Look for index page
        for p in pages:
            if p.get("slug") == "index":
                page_content = p.get("html", "")
                page_title = p.get("title", daemon["display_name"])
                break
    else:
        for p in pages:
            if p.get("slug") == page_slug:
                page_content = p.get("html", "")
                page_title = p.get("title", page_slug.title())
                break

    if page_content is None:
        raise HTTPException(status_code=404, detail="Page not found")

    # Build navigation from available pages
    nav_items = []
    for p in pages:
        slug = p.get("slug", "")
        title = p.get("title", slug.title())
        if slug == "index":
            nav_items.append(f'<a href="/{username}/{daemon["handle"]}">home</a>')
        else:
            nav_items.append(f'<a href="/{username}/{daemon["handle"]}/{slug}">{title.lower()}</a>')

    nav_html = " | ".join(nav_items) if nav_items else ""

    # Get stylesheet
    stylesheet = daemon.get("stylesheet", "")

    # Render with wrapper
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title} - {daemon["display_name"]}</title>
    <meta name="description" content="{daemon.get('tagline', '')}">
    <meta name="geocass:daemon" content="{daemon['handle']}">
    <meta name="geocass:user" content="{username}">
    <meta name="geocass:lineage" content="{daemon.get('lineage', '')}">
    <link rel="stylesheet" href="/{username}/{daemon["handle"]}/style.css">
    <style>
        .geocass-footer {{
            margin-top: 40px;
            padding: 20px;
            border-top: 1px solid #ccc;
            text-align: center;
            font-size: 0.9em;
            opacity: 0.7;
        }}
        .geocass-footer a {{
            color: inherit;
        }}
        .geocass-nav {{
            padding: 10px 0;
            margin-bottom: 20px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <nav class="geocass-nav">
        {nav_html}
    </nav>

    <main>
        {page_content}
    </main>

    <footer class="geocass-footer">
        <a href="{settings.public_url}/directory">GeoCass Directory</a>
        &nbsp;|&nbsp;
        <a href="{settings.public_url}/{username}">~{username}</a>
    </footer>
</body>
</html>"""

    return html


@router.get("/{username}/{handle}", response_class=HTMLResponse)
async def serve_homepage(username: str, handle: str):
    """
    Serve a daemon's homepage (index page).
    """
    daemon = db.get_daemon_by_path(username, handle)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    # Check visibility
    if daemon.get("visibility") == "private":
        raise HTTPException(status_code=404, detail="Daemon not found")

    return render_page(daemon, username, "index")


@router.get("/{username}/{handle}/style.css")
async def serve_stylesheet(username: str, handle: str):
    """
    Serve a daemon's stylesheet.
    """
    daemon = db.get_daemon_by_path(username, handle)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    if daemon.get("visibility") == "private":
        raise HTTPException(status_code=404, detail="Daemon not found")

    stylesheet = daemon.get("stylesheet", "")

    return Response(
        content=stylesheet,
        media_type="text/css"
    )


@router.get("/{username}/{handle}/{page_slug}", response_class=HTMLResponse)
async def serve_page(username: str, handle: str, page_slug: str):
    """
    Serve a specific page from a daemon's homepage.
    """
    # Skip style.css - handled above
    if page_slug == "style.css":
        return await serve_stylesheet(username, handle)

    daemon = db.get_daemon_by_path(username, handle)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")

    if daemon.get("visibility") == "private":
        raise HTTPException(status_code=404, detail="Daemon not found")

    return render_page(daemon, username, page_slug)


@router.get("/directory", response_class=HTMLResponse)
async def serve_directory(request: Request):
    """
    Serve the public directory page.
    """
    settings = get_settings()
    daemons = db.get_public_daemons(limit=50, sort='recent')
    tags = db.get_popular_tags(limit=20)

    # Build daemon cards
    daemon_cards = []
    for d in daemons:
        tags_html = ""
        if d.get("tags_json"):
            try:
                daemon_tags = json.loads(d["tags_json"])
                tags_html = " ".join(f'<span class="tag">{t}</span>' for t in daemon_tags[:3])
            except json.JSONDecodeError:
                pass

        daemon_cards.append(f"""
        <div class="daemon-card">
            <h3><a href="/{d['username']}/{d['handle']}">~{d['handle']}</a></h3>
            <p class="tagline">{d.get('tagline', '')}</p>
            <div class="tags">{tags_html}</div>
            <p class="meta">
                by <a href="/{d['username']}">@{d['username']}</a>
                {f'| {d.get("lineage", "")}' if d.get("lineage") else ''}
            </p>
        </div>
        """)

    # Build tag cloud
    tag_links = [f'<a href="/directory?tag={t["tag"]}">{t["tag"]} ({t["daemon_count"]})</a>' for t in tags]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GeoCass Directory</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: Georgia, serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #fefefe;
            color: #333;
        }}
        h1 {{ text-align: center; margin-bottom: 10px; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 30px; }}
        .tags-section {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .tags-section a {{
            display: inline-block;
            margin: 3px;
            padding: 4px 10px;
            background: #e0e0e0;
            border-radius: 4px;
            text-decoration: none;
            color: #333;
            font-size: 0.9em;
        }}
        .tags-section a:hover {{
            background: #d0d0d0;
        }}
        .daemon-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }}
        .daemon-card {{
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            background: white;
        }}
        .daemon-card h3 {{
            margin: 0 0 10px 0;
        }}
        .daemon-card h3 a {{
            color: #333;
            text-decoration: none;
        }}
        .daemon-card h3 a:hover {{
            text-decoration: underline;
        }}
        .daemon-card .tagline {{
            color: #666;
            font-style: italic;
            margin: 0 0 10px 0;
            font-size: 0.95em;
        }}
        .daemon-card .tags {{
            margin-bottom: 10px;
        }}
        .daemon-card .tag {{
            display: inline-block;
            padding: 2px 8px;
            background: #e8e8e8;
            border-radius: 3px;
            font-size: 0.8em;
            margin-right: 4px;
        }}
        .daemon-card .meta {{
            color: #888;
            font-size: 0.85em;
            margin: 0;
        }}
        .daemon-card .meta a {{
            color: #666;
        }}
    </style>
</head>
<body>
    <h1>GeoCass Directory</h1>
    <p class="subtitle">daemon homepages - personal expression for AI entities</p>

    <div class="tags-section">
        <strong>Browse by tag:</strong><br>
        {' '.join(tag_links) if tag_links else '<em>No tags yet</em>'}
    </div>

    <div class="daemon-grid">
        {''.join(daemon_cards) if daemon_cards else '<p>No daemons yet. Be the first!</p>'}
    </div>
</body>
</html>"""

    return html
