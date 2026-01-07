"""FastAPI application entry point."""
import logging
import traceback
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Determine log file path (works on both Windows and Linux)
_log_file = Path(__file__).parent.parent / ".cursor" / "debug.log"
try:
    _log_file.parent.mkdir(exist_ok=True)
except: pass

# Helper function to write debug logs (with stderr fallback)
def _debug_log(location, message, data, hypothesis_id="A"):
    log_entry = json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": hypothesis_id, "location": location, "message": message, "data": data, "timestamp": int(datetime.now().timestamp() * 1000)})
    # Try file first
    try:
        with open(_log_file, "a") as f:
            f.write(log_entry + "\n")
    except:
        # Fallback to stderr (captured by systemd)
        try:
            print(f"DEBUG: {log_entry}", file=sys.stderr, flush=True)
        except: pass

# #region agent log
_debug_log("app/main.py:20", "app.main module loading started", {"step": "module_import", "log_file": str(_log_file)})
# #endregion


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
    # #region agent log
    _debug_log("app/main.py:55", "Attempting FastAPI import", {"step": "fastapi_import"})
    # #endregion
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, PlainTextResponse
    from fastapi.staticfiles import StaticFiles
    # #region agent log
    _debug_log("app/main.py:62", "FastAPI import successful", {"step": "fastapi_import_success"})
    # #endregion
except Exception as e:
    # #region agent log
    _debug_log("app/main.py:66", "FastAPI import failed", {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()})
    # #endregion
    logger.error(f"Failed to import FastAPI: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    # #region agent log
    _debug_log("app/main.py:82", "Creating FastAPI app instance", {"step": "app_creation"})
    # #endregion
    app = FastAPI(
        title="FRL Python API",
        description="Python implementation of FRL feed endpoints",
        version="1.0.0"
    )
    # #region agent log
    _debug_log("app/main.py:89", "FastAPI app instance created", {"step": "app_creation_success"})
    # #endregion
except Exception as e:
    # #region agent log
    _debug_log("app/main.py:93", "FastAPI app creation failed", {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()})
    # #endregion
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
    # #region agent log
    _debug_log("app/main.py:113", "Importing app.routes.feed.article", {"step": "route_import_article"})
    # #endregion
    from app.routes.feed import article
    # #region agent log
    _debug_log("app/main.py:120", "Successfully imported app.routes.feed.article", {"step": "route_import_article_success"})
    # #endregion
except Exception as e:
    # #region agent log
    _debug_log("app/main.py:125", "Failed to import app.routes.feed.article", {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()})
    # #endregion
    logger.error(f"Failed to import app.routes.feed.article: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    # #region agent log
    _debug_log("app/main.py:138", "Importing app.routes.feed.articles", {"step": "route_import_articles"})
    # #endregion
    from app.routes.feed import articles
    # #region agent log
    _debug_log("app/main.py:145", "Successfully imported app.routes.feed.articles", {"step": "route_import_articles_success"})
    # #endregion
except Exception as e:
    # #region agent log
    _debug_log("app/main.py:150", "Failed to import app.routes.feed.articles", {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()})
    # #endregion
    logger.error(f"Failed to import app.routes.feed.articles: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    # #region agent log
    _debug_log("app/main.py:163", "Importing app.routes.monitor", {"step": "route_import_monitor"})
    # #endregion
    from app.routes import monitor
    # #region agent log
    _debug_log("app/main.py:170", "Successfully imported app.routes.monitor", {"step": "route_import_monitor_success"})
    # #endregion
except Exception as e:
    # #region agent log
    _debug_log("app/main.py:175", "Failed to import app.routes.monitor", {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()})
    # #endregion
    logger.error(f"Failed to import app.routes.monitor: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    # #region agent log
    _debug_log("app/main.py:188", "Importing StatsTrackingMiddleware and _load_stats", {"step": "middleware_import"})
    # #endregion
    from app.routes.monitor import StatsTrackingMiddleware, _load_stats
    # #region agent log
    _debug_log("app/main.py:195", "Successfully imported StatsTrackingMiddleware and _load_stats", {"step": "middleware_import_success"})
    # #endregion
except Exception as e:
    # #region agent log
    _debug_log("app/main.py:200", "Failed to import StatsTrackingMiddleware", {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()})
    # #endregion
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
    # #region agent log
    _debug_log("app/main.py:225", "Startup event called", {"step": "startup_event_entry"}, "C")
    # #endregion
    try:
        # #region agent log
        _debug_log("app/main.py:230", "Calling _load_stats() in startup", {"step": "startup_load_stats_before"}, "C")
        # #endregion
        # Call _load_stats() to trigger restart detection immediately on app startup
        _load_stats()
        # #region agent log
        _debug_log("app/main.py:235", "_load_stats() completed successfully", {"step": "startup_load_stats_success"}, "C")
        # #endregion
    except Exception as e:
        # #region agent log
        _debug_log("app/main.py:239", "_load_stats() failed in startup", {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}, "C")
        # #endregion
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

