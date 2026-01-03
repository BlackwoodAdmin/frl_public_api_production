"""Gunicorn configuration for production."""
import multiprocessing
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("gunicorn.error")

# Server socket
bind = f"127.0.0.1:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = os.getenv("LOG_LEVEL", "INFO").lower()

# Process naming
proc_name = "frl-python-api"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed in future)
# keyfile = None
# certfile = None


def on_starting(server):
    """Called just before the master process is initialized."""
    logger.info("=" * 80)
    logger.info("Gunicorn starting...")
    logger.info(f"Bind: {bind}")
    logger.info(f"Workers: {workers}")
    logger.info(f"Worker class: {worker_class}")
    logger.info("=" * 80)


def when_ready(server):
    """Called just after the server is started."""
    logger.info("=" * 80)
    logger.info("Gunicorn is ready to accept connections")
    logger.info(f"Listening on: {bind}")
    logger.info(f"Workers: {workers}")
    logger.info("=" * 80)


def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal."""
    logger.warning(f"Worker {worker.pid} received INT/QUIT signal")


def worker_abort(worker):
    """Called when a worker receives the ABRT signal."""
    logger.error(f"Worker {worker.pid} received ABRT signal (worker abort)")
    import traceback
    logger.error(traceback.format_exc())


def on_exit(server):
    """Called just before exiting Gunicorn."""
    logger.info("=" * 80)
    logger.info("Gunicorn is shutting down")
    logger.info("=" * 80)


