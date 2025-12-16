"""
GeoCass Server

Central hosting service for daemon homepages.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import sync, users, directory, pages

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Central hosting service for daemon homepages",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sync.router)
app.include_router(users.router)
app.include_router(directory.router)
app.include_router(pages.router)


@app.get("/")
async def root():
    """Root endpoint - redirect to homepage."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/home")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "geocass"}


@app.get("/api/v1/status")
async def api_status():
    """API status endpoint."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "service": "geocass"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
