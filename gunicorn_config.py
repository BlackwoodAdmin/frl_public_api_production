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
try:
    _log_file.parent.mkdir(exist_ok=True)
except: pass

# Helper function to write debug logs (with stderr fallback)
def _debug_log(location, message, data, hypothesis_id="B"):
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
_debug_log("gunicorn_config.py:18", "Gunicorn config module loading", {"step": "module_import", "log_file": str(_log_file)})
# #endregion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("gunicorn.error")

# #region agent log
_debug_log("gunicorn_config.py:35", "Gunicorn config logger configured", {"step": "logger_setup"})
# #endregion

# Server socket
port = os.getenv('PORT', '8000')
bind_addr = f"127.0.0.1:{port}"
# #region agent log
_debug_log("gunicorn_config.py:42", "Gunicorn bind address configured", {"bind": bind_addr, "port": port, "port_from_env": os.getenv('PORT')})
# #endregion
bind = bind_addr
backlog = 2048

# Worker processes
cpu_count = multiprocessing.cpu_count()
workers_count = cpu_count * 2 + 1
# #region agent log
_debug_log("gunicorn_config.py:50", "Gunicorn workers configured", {"cpu_count": cpu_count, "workers": workers_count, "worker_class": "uvicorn.workers.UvicornWorker"})
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
        _debug_log("gunicorn_config.py:84", "Gunicorn on_starting hook called", {"server_address": str(server.address) if hasattr(server, 'address') else None})
    except Exception as e:
        _debug_log("gunicorn_config.py:84", "Gunicorn on_starting hook error", {"error": str(e)})
    # #endregion
    logger.info("Gunicorn starting...")


def when_ready(server):
    """Called just after the server is started."""
    # #region agent log
    try:
        _debug_log("gunicorn_config.py:97", "Gunicorn when_ready hook called", {"server_address": str(server.address) if hasattr(server, 'address') else None})
    except Exception as e:
        _debug_log("gunicorn_config.py:97", "Gunicorn when_ready hook error", {"error": str(e)})
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
    _debug_log("gunicorn_config.py:116", "Gunicorn on_exit hook called", {})
    # #endregion
    logger.info("Gunicorn is shutting down")


