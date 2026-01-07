"""Gunicorn configuration for production."""
import multiprocessing
import os
import logging
import sys
import json
from datetime import datetime
from pathlib import Path

# Determine log file path (works on both Windows and Linux)
_log_file = Path(__file__).parent / ".cursor" / "debug.log"
_log_file.parent.mkdir(exist_ok=True)

# #region agent log
try:
    with open(_log_file, "a") as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "gunicorn_config.py:10", "message": "Gunicorn config module loading", "data": {"step": "module_import", "log_file": str(_log_file)}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
except: pass
# #endregion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("gunicorn.error")

# #region agent log
try:
    with open(_log_file, "a") as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "gunicorn_config.py:21", "message": "Gunicorn config logger configured", "data": {"step": "logger_setup"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
except: pass
# #endregion

# Server socket
port = os.getenv('PORT', '8000')
bind_addr = f"127.0.0.1:{port}"
# #region agent log
try:
    with open(_log_file, "a") as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "gunicorn_config.py:28", "message": "Gunicorn bind address configured", "data": {"bind": bind_addr, "port": port, "port_from_env": os.getenv('PORT')}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
except: pass
# #endregion
bind = bind_addr
backlog = 2048

# Worker processes
cpu_count = multiprocessing.cpu_count()
workers_count = cpu_count * 2 + 1
# #region agent log
try:
    with open(_log_file, "a") as f:
        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "gunicorn_config.py:36", "message": "Gunicorn workers configured", "data": {"cpu_count": cpu_count, "workers": workers_count, "worker_class": "uvicorn.workers.UvicornWorker"}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
except: pass
# #endregion
workers = workers_count
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
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "gunicorn_config.py:60", "message": "Gunicorn on_starting hook called", "data": {"server_address": str(server.address) if hasattr(server, 'address') else None}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except Exception as e:
        try:
            with open(_log_file, "a") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "gunicorn_config.py:60", "message": "Gunicorn on_starting hook error", "data": {"error": str(e)}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
        except: pass
    # #endregion
    logger.info("Gunicorn starting...")


def when_ready(server):
    """Called just after the server is started."""
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "gunicorn_config.py:73", "message": "Gunicorn when_ready hook called", "data": {"server_address": str(server.address) if hasattr(server, 'address') else None}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except Exception as e:
        try:
            with open(_log_file, "a") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "gunicorn_config.py:73", "message": "Gunicorn when_ready hook error", "data": {"error": str(e)}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
        except: pass
    # #endregion
    logger.info("Gunicorn is ready to accept connections")


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
    # #region agent log
    try:
        with open(_log_file, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "gunicorn_config.py:92", "message": "Gunicorn on_exit hook called", "data": {}, "timestamp": int(datetime.now().timestamp() * 1000)}) + "\n")
    except: pass
    # #endregion
    logger.info("Gunicorn is shutting down")


