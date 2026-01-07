"""FastAPI application entry point."""
import logging
import traceback
import os
from pathlib import Path


class SocketErrorFilter(logging.Filter):
    """Filter out harmless Gunicorn socket closing errors."""
    def filter(self, record):
        message = record.getMessage()
        # Filter out socket closing errors
        if "Error while closing socket" in message and "Bad file descriptor" in message:
            return False
        return True


# Configure logging FIRST before any other imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add filter to root logger to catch all loggers including Gunicorn
logging.getLogger().addFilter(SocketErrorFilter())

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, PlainTextResponse
    from fastapi.staticfiles import StaticFiles
except Exception as e:
    logger.error(f"Failed to import FastAPI: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    app = FastAPI(
        title="FRL Python API",
        description="Python implementation of FRL feed endpoints",
        version="1.0.0"
    )
except Exception as e:
    logger.error(f"Failed to create FastAPI app: {e}")
    logger.error(traceback.format_exc())
    raise


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "FRL Python API", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/alive")
async def alive():
    """DNS rollover health check endpoint."""
    return PlainTextResponse(content="alive")


# Import routes
try:
    from app.routes.feed import article
except Exception as e:
    logger.error(f"Failed to import app.routes.feed.article: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    from app.routes.feed import articles
except Exception as e:
    logger.error(f"Failed to import app.routes.feed.articles: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    from app.routes import monitor
except Exception as e:
    logger.error(f"Failed to import app.routes.monitor: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    from app.routes.monitor import StatsTrackingMiddleware, _load_stats
except Exception as e:
    logger.error(f"Failed to import StatsTrackingMiddleware: {e}")
    logger.error(traceback.format_exc())
    raise

# Add request tracking middleware (before routes to track all requests)
try:
    app.add_middleware(StatsTrackingMiddleware)
except Exception as e:
    logger.error(f"Failed to register StatsTrackingMiddleware: {e}")
    logger.error(traceback.format_exc())
    raise

# Mount static files for external_files directory
try:
    # Get the app root directory (parent of app/)
    app_root = Path(__file__).parent.parent
    external_files_dir = app_root / "external_files"
    
    # Create external_files directory if it doesn't exist
    external_files_dir.mkdir(exist_ok=True)
    logger.info(f"External files directory ready at: {external_files_dir}")
    
    # Mount static files at /external_files/
    app.mount("/external_files", StaticFiles(directory=str(external_files_dir)), name="external_files")
except Exception as e:
    logger.error(f"Failed to mount external_files static directory: {e}")
    logger.error(traceback.format_exc())
    # Don't raise - allow app to continue even if static files fail

# Include routers
try:
    app.include_router(article.router, prefix="/feed", tags=["feed"])
except Exception as e:
    logger.error(f"Failed to include article router: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    app.include_router(articles.router, prefix="/feed", tags=["feed"])
except Exception as e:
    logger.error(f"Failed to include articles router: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    app.include_router(monitor.router, prefix="/monitor", tags=["monitoring"])
except Exception as e:
    logger.error(f"Failed to include monitor router: {e}")
    logger.error(traceback.format_exc())
    raise


@app.on_event("startup")
async def startup_event():
    """Detect app restart and reset stats on startup."""
    try:
        # Call _load_stats() to trigger restart detection immediately on app startup
        _load_stats()
    except Exception as e:
        # Don't crash app startup if stats loading fails
        logger.error(f"Failed to load stats on startup: {e}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

