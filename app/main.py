"""FastAPI application entry point."""
import logging
import traceback


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
logger.info("=" * 80)
logger.info("Starting FRL Python API application initialization")
logger.info("=" * 80)

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    logger.info("✓ Successfully imported FastAPI and HTMLResponse")
except Exception as e:
    logger.error(f"✗ Failed to import FastAPI: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    app = FastAPI(
        title="FRL Python API",
        description="Python implementation of FRL feed endpoints",
        version="1.0.0"
    )
    logger.info("✓ Successfully created FastAPI app instance")
except Exception as e:
    logger.error(f"✗ Failed to create FastAPI app: {e}")
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


# Import routes
logger.info("Starting route imports...")

try:
    logger.info("Importing app.routes.feed.article...")
    from app.routes.feed import article
    logger.info("✓ Successfully imported app.routes.feed.article")
except Exception as e:
    logger.error(f"✗ Failed to import app.routes.feed.article: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    logger.info("Importing app.routes.feed.articles...")
    from app.routes.feed import articles
    logger.info("✓ Successfully imported app.routes.feed.articles")
except Exception as e:
    logger.error(f"✗ Failed to import app.routes.feed.articles: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    logger.info("Importing app.routes.monitor...")
    from app.routes import monitor
    logger.info("✓ Successfully imported app.routes.monitor")
except Exception as e:
    logger.error(f"✗ Failed to import app.routes.monitor: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    logger.info("Importing StatsTrackingMiddleware...")
    from app.routes.monitor import StatsTrackingMiddleware
    logger.info("✓ Successfully imported StatsTrackingMiddleware")
except Exception as e:
    logger.error(f"✗ Failed to import StatsTrackingMiddleware: {e}")
    logger.error(traceback.format_exc())
    raise

# Add request tracking middleware (before routes to track all requests)
try:
    logger.info("Registering StatsTrackingMiddleware...")
    app.add_middleware(StatsTrackingMiddleware)
    logger.info("✓ Successfully registered StatsTrackingMiddleware")
except Exception as e:
    logger.error(f"✗ Failed to register StatsTrackingMiddleware: {e}")
    logger.error(traceback.format_exc())
    raise

# Include routers
try:
    logger.info("Including article router...")
    app.include_router(article.router, prefix="/feed", tags=["feed"])
    logger.info("✓ Successfully included article router")
except Exception as e:
    logger.error(f"✗ Failed to include article router: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    logger.info("Including articles router...")
    app.include_router(articles.router, prefix="/feed", tags=["feed"])
    logger.info("✓ Successfully included articles router")
except Exception as e:
    logger.error(f"✗ Failed to include articles router: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    logger.info("Including monitor router...")
    app.include_router(monitor.router, prefix="/monitor", tags=["monitoring"])
    logger.info("✓ Successfully included monitor router")
except Exception as e:
    logger.error(f"✗ Failed to include monitor router: {e}")
    logger.error(traceback.format_exc())
    raise

logger.info("=" * 80)
logger.info("Application initialization completed successfully")
logger.info("=" * 80)


if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

