"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="FRL Python API",
    description="Python implementation of FRL feed endpoints",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "FRL Python API", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import routes
from app.routes.feed import article, articles
app.include_router(article.router, prefix="/feed", tags=["feed"])
app.include_router(articles.router, prefix="/feed", tags=["feed"])


if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

