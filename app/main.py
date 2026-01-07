"""FastAPI application entry point."""
import logging
import traceback
import os
import json
from pathlib import Path
from datetime import datetime

# Determine log file path (works on both Windows and Linux)
_log_file = Path(__file__).parent.parent / ".cursor" / "debug.log"
_log_file.parent.mkdir(exist_ok=True)

# #region agent log
try:
    with open(_log_file, "a") as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:12", "message": "app.main module loading started", "data": {"step": "module_import", "log_file": str(_log_file)}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
except: pass
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
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:34", "message": "Attempting FastAPI import", "data": {"step": "fastapi_import"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, PlainTextResponse
    from fastapi.staticfiles import StaticFiles
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:40", "message": "FastAPI import successful", "data": {"step": "fastapi_import_success"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:45", "message": "FastAPI import failed", "data": {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
    logger.error(f"Failed to import FastAPI: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:52", "message": "Creating FastAPI app instance", "data": {"step": "app_creation"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
    app = FastAPI(
        title="FRL Python API",
        description="Python implementation of FRL feed endpoints",
        version="1.0.0"
    )
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:61", "message": "FastAPI app instance created", "data": {"step": "app_creation_success"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:66", "message": "FastAPI app creation failed", "data": {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
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
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:75", "message": "Importing app.routes.feed.article", "data": {"step": "route_import_article"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
    from app.routes.feed import article
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:80", "message": "Successfully imported app.routes.feed.article", "data": {"step": "route_import_article_success"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:85", "message": "Failed to import app.routes.feed.article", "data": {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
    logger.error(f"Failed to import app.routes.feed.article: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:92", "message": "Importing app.routes.feed.articles", "data": {"step": "route_import_articles"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
    from app.routes.feed import articles
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:97", "message": "Successfully imported app.routes.feed.articles", "data": {"step": "route_import_articles_success"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:102", "message": "Failed to import app.routes.feed.articles", "data": {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
    logger.error(f"Failed to import app.routes.feed.articles: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:109", "message": "Importing app.routes.monitor", "data": {"step": "route_import_monitor"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
    from app.routes import monitor
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:114", "message": "Successfully imported app.routes.monitor", "data": {"step": "route_import_monitor_success"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "app/main.py:119", "message": "Failed to import app.routes.monitor", "data": {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
    logger.error(f"Failed to import app.routes.monitor: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "app/main.py:126", "message": "Importing StatsTrackingMiddleware and _load_stats", "data": {"step": "middleware_import"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
    from app.routes.monitor import StatsTrackingMiddleware, _load_stats
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "app/main.py:131", "message": "Successfully imported StatsTrackingMiddleware and _load_stats", "data": {"step": "middleware_import_success"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "app/main.py:136", "message": "Failed to import StatsTrackingMiddleware", "data": {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
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
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "app/main.py:200", "message": "Startup event called", "data": {"step": "startup_event_entry"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
    try:
        # #region agent log
        try:
            with open(_log_file, "a") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "app/main.py:203", "message": "Calling _load_stats() in startup", "data": {"step": "startup_load_stats_before"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
        except: pass
        # #endregion
        # Call _load_stats() to trigger restart detection immediately on app startup
        _load_stats()
        # #region agent log
        try:
            with open(_log_file, "a") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "app/main.py:208", "message": "_load_stats() completed successfully", "data": {"step": "startup_load_stats_success"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
        except: pass
        # #endregion
    except Exception as e:
        # #region agent log
        try:
            with open(_log_file, "a") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "app/main.py:213", "message": "_load_stats() failed in startup", "data": {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
        except: pass
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

