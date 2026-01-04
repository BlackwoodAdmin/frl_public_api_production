"""Monitoring endpoints for Gunicorn workers and system health."""
import logging
import traceback
import hashlib

# Get logger early
logger = logging.getLogger(__name__)

try:
    from fastapi import APIRouter, Request, HTTPException, status
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
    from starlette.middleware.base import BaseHTTPMiddleware
    from typing import List, Dict, Any, Optional
    import psutil
    import os
    import time
    import json
    import fcntl
    import subprocess
    import shutil
    import threading
    from datetime import datetime
    from pathlib import Path
except Exception as e:
    logger.error(f"Failed to import standard libraries: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    from app.database import db
except Exception as e:
    logger.error(f"Failed to import app.database: {e}")
    logger.error(traceback.format_exc())
    raise

router = APIRouter()

def check_auth_for_html(request: Request):
    """Check authentication for HTML endpoints, returns (username, None) if authenticated, (None, RedirectResponse) if not."""
    import base64
    from app.services.auth import validate_dashboard_credentials
    
    logger.debug("check_auth_for_html: Authentication check started")
    
    try:
        # Extract Authorization header
        auth_header = request.headers.get("Authorization")
        logger.debug(f"check_auth_for_html: Authorization header present: {auth_header is not None}")
        
        if not auth_header or not auth_header.startswith("Basic "):
            if not auth_header:
                logger.debug("check_auth_for_html: Authorization header is missing")
            elif not auth_header.startswith("Basic "):
                logger.debug(f"check_auth_for_html: Authorization header does not start with 'Basic ': {auth_header[:20]}...")
            return None, RedirectResponse(url="/monitor/login", status_code=302)
        
        # Decode Basic Auth credentials
        encoded_credentials = auth_header.split(" ")[1]
        logger.debug(f"check_auth_for_html: Encoded credentials length: {len(encoded_credentials)}")
        
        try:
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            username, password = decoded_credentials.split(":", 1)
            logger.debug(f"check_auth_for_html: Credentials decoded successfully. Username: {username}, Password: **** (masked)")
        except (ValueError, UnicodeDecodeError) as decode_error:
            logger.warning(f"check_auth_for_html: Failed to decode credentials: {decode_error}")
            return None, RedirectResponse(url="/monitor/login", status_code=302)
        
        # Validate credentials
        logger.debug(f"check_auth_for_html: Calling validate_dashboard_credentials for username: {username}")
        validation_result = validate_dashboard_credentials(username, password)
        logger.debug(f"check_auth_for_html: Validation result: {validation_result}")
        
        if not validation_result:
            logger.warning(f"check_auth_for_html: Credential validation failed for username: {username}")
            return None, RedirectResponse(url="/monitor/login", status_code=302)
        
        logger.info(f"check_auth_for_html: Authentication successful for username: {username}")
        return username, None
    except Exception as e:
        logger.error(f"check_auth_for_html: Error in HTML dashboard authentication: {e}")
        logger.error(f"check_auth_for_html: Exception traceback: {traceback.format_exc()}")
        return None, RedirectResponse(url="/monitor/login", status_code=302)

# File-based stats storage (shared across workers)
STATS_FILE = Path("/var/run/frl-python-api/stats.json")
STATS_LOCK_FILE = Path("/var/run/frl-python-api/stats.lock")

# Cache for system metrics (reduces file I/O and process enumeration)
_system_metrics_cache = {
    "data": None,
    "timestamp": 0,
    "lock": threading.Lock(),
    "cpu_baseline_set": False  # Track if CPU baseline has been established
}
SYSTEM_METRICS_CACHE_TTL = 0.5  # Cache for 0.5 seconds

# Cache for process enumeration (reduces CPU overhead)
_process_enumeration_cache = {
    "data": None,
    "timestamp": 0,
    "lock": threading.Lock()
}
PROCESS_ENUMERATION_CACHE_TTL = 0.5  # Cache for 0.5 seconds

# Log file configuration
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "/var/log/frl-python-api/app.log")
USE_JOURNALCTL = os.getenv("USE_JOURNALCTL", "false").lower() == "true"


def _find_journalctl_path() -> str:
    """Find the path to journalctl executable."""
    logger.debug("Finding journalctl path...")
    # Common system paths for journalctl
    common_paths = [
        "/usr/bin/journalctl",
        "/bin/journalctl",
        "/usr/sbin/journalctl",
        "/sbin/journalctl"
    ]
    
    # First try to find it in PATH
    journalctl_path = shutil.which("journalctl")
    if journalctl_path:
        return journalctl_path
    
    # If not in PATH, try common system paths
    for path in common_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    
    # If still not found, return default
    logger.warning("⚠ journalctl not found in PATH or common locations, using default")
    return "journalctl"  # Will fail with better error message

# Cache the journalctl path
try:
    JOURNALCTL_PATH = _find_journalctl_path()
except Exception as e:
    logger.error(f"Failed to find journalctl path: {e}")
    logger.error(traceback.format_exc())
    JOURNALCTL_PATH = "journalctl"  # Fallback

# Initialize stats file if it doesn't exist
try:
    if not STATS_FILE.exists():
        try:
            # Ensure directory exists
            STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            initial_stats = {
                "total_requests": 0,
                "request_times": [],
                "errors": 0,
                "start_time": time.time(),
                "last_minute_requests": [],
                "last_reset_time": time.time(),
                "app_session_id": None,  # Will be set on first load based on master PID
            }
            with open(STATS_FILE, 'w') as f:
                json.dump(initial_stats, f)
        except Exception as e:
            logger.error(f"Failed to initialize stats file {STATS_FILE}: {e}")
            logger.error(traceback.format_exc())
except Exception as e:
    logger.error(f"Error checking stats file: {e}")
    logger.error(traceback.format_exc())


def _load_stats() -> Dict[str, Any]:
    """Load stats from file with locking.
    
    Also handles 3-hour automatic reset of error counts and migration of stats format.
    """
    try:
        # Ensure lock file exists
        STATS_LOCK_FILE.touch(exist_ok=True)
        
        # Check if file exists first (without lock to avoid unnecessary locking)
        if STATS_FILE.exists():
            # File exists - read with shared lock first
            with open(STATS_LOCK_FILE, 'r+') as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                try:
                    with open(STATS_FILE, 'r') as f:
                        stats = json.load(f)
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            
            current_time = time.time()
            
            # Migration: Add missing fields if needed
            needs_migration = False
            if "last_reset_time" not in stats:
                stats["last_reset_time"] = current_time
                needs_migration = True
            if "app_session_id" not in stats:
                stats["app_session_id"] = None  # Will trigger reset below
                needs_migration = True
            
            if needs_migration:
                # Save migrated stats (will use exclusive lock in _save_stats)
                _save_stats(stats)
                # Continue to session check below (will reset if app_session_id is None)
            
            # Check if app session ID matches (app restart detection using master PID)
            # Get current master PID - all workers share the same master PID
            _, current_master_pid = _get_gunicorn_processes()
            stored_session_id = stats.get("app_session_id")
            
            # If master PID not found (e.g., dev mode), skip restart detection
            if current_master_pid is not None:
                if stored_session_id is None:
                    # First time setting session ID (migration or new install)
                    # Need exclusive lock to update
                    with open(STATS_LOCK_FILE, 'r+') as lock_file:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
                        try:
                            # Reload stats and set session ID
                            with open(STATS_FILE, 'r') as f:
                                stats = json.load(f)
                            
                            if stats.get("app_session_id") is None:
                                stats["app_session_id"] = current_master_pid
                                with open(STATS_FILE, 'w') as f:
                                    json.dump(stats, f)
                        finally:
                            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                elif stored_session_id != current_master_pid:
                    # App has restarted - reset error-related counters
                    # Need exclusive lock to reset - use double-check pattern
                    with open(STATS_LOCK_FILE, 'r+') as lock_file:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
                        try:
                            # Double-check: reload stats in case another process already reset
                            with open(STATS_FILE, 'r') as f:
                                stats = json.load(f)
                            
                            # Get master PID again and check if reset is still needed
                            _, current_master_pid = _get_gunicorn_processes()
                            stored_session_id = stats.get("app_session_id")
                            if current_master_pid is not None and stored_session_id is not None and stored_session_id != current_master_pid:
                                # Reset error-related counters on app restart
                                stats["errors"] = 0
                                stats["total_requests"] = 0
                                stats["request_times"] = []
                                stats["last_minute_requests"] = []
                                stats["last_reset_time"] = current_time
                                stats["start_time"] = current_time
                                stats["app_session_id"] = current_master_pid
                                
                                # Save reset stats
                                with open(STATS_FILE, 'w') as f:
                                    json.dump(stats, f)
                                logger.info(f"Reset error counts on app restart. Errors: 0, Total requests: 0")
                        finally:
                            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            
            # Check if 3 hours (10800 seconds) have passed since last reset
            time_since_reset = current_time - stats.get("last_reset_time", current_time)
            if time_since_reset >= 10800:  # 3 hours
                # Need exclusive lock to reset - use double-check pattern
                with open(STATS_LOCK_FILE, 'r+') as lock_file:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
                    try:
                        # Double-check: reload stats in case another process already reset
                        with open(STATS_FILE, 'r') as f:
                            stats = json.load(f)
                        
                        # Check again if reset is still needed
                        time_since_reset = current_time - stats.get("last_reset_time", current_time)
                        if time_since_reset >= 10800:
                            # Reset error-related counters (keep total_requests for cumulative count)
                            stats["errors"] = 0
                            stats["request_times"] = []
                            stats["last_reset_time"] = current_time
                            # Keep start_time, total_requests, and last_minute_requests unchanged
                            
                            # Save reset stats
                            with open(STATS_FILE, 'w') as f:
                                json.dump(stats, f)
                            logger.info(f"Reset error counts after 3 hours. Errors: 0")
                    finally:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            
            return stats
        else:
            # File doesn't exist - create it with exclusive lock
            with open(STATS_LOCK_FILE, 'r+') as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
                try:
                    # Double-check file doesn't exist (another process might have created it)
                    if STATS_FILE.exists():
                        with open(STATS_FILE, 'r') as f:
                            return json.load(f)
                    
                    # Create directory if it doesn't exist
                    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Initialize stats
                    initial_stats = {
                        "total_requests": 0,
                        "request_times": [],
                        "errors": 0,
                        "start_time": time.time(),
                        "last_minute_requests": [],
                        "last_reset_time": time.time(),
                        "app_session_id": None,  # Will be set on first load based on master PID
                    }
                    
                    # Create file
                    with open(STATS_FILE, 'w') as f:
                        json.dump(initial_stats, f)
                    logger.info(f"Created stats file: {STATS_FILE}")
                    return initial_stats
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Error loading stats: {e}")
        return {
            "total_requests": 0,
            "request_times": [],
            "errors": 0,
            "start_time": time.time(),
            "last_minute_requests": [],
            "last_reset_time": time.time(),
            "app_session_id": None,  # Will be set on first load based on master PID
        }


def _save_stats(stats: Dict[str, Any]):
    """Save stats to file with locking."""
    try:
        # Ensure directory exists
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure lock file exists
        STATS_LOCK_FILE.touch(exist_ok=True)
        
        with open(STATS_LOCK_FILE, 'r+') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
            try:
                with open(STATS_FILE, 'w') as f:
                    json.dump(stats, f)
                logger.debug(f"Saving stats: total_requests={stats.get('total_requests', 0)}, errors={stats.get('errors', 0)}")
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Error saving stats to {STATS_FILE}: {e}")


def _update_stats(update_func):
    """Atomically update stats."""
    stats = _load_stats()
    update_func(stats)
    _save_stats(stats)


class StatsTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request statistics."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip tracking for monitoring endpoints to avoid recursion
        if request.url.path.startswith("/monitor"):
            return await call_next(request)
        
        # Record request start time
        logger.debug(f"Tracking request: {request.method} {request.url.path}")
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Track errors
            def update_error(stats):
                stats["errors"] += 1
                stats["total_requests"] += 1
                current_time = time.time()
                stats["last_minute_requests"].append(current_time)
                # Clean old timestamps (older than 5 minutes)
                stats["last_minute_requests"] = [
                    t for t in stats["last_minute_requests"]
                    if current_time - t < 300
                ]
            _update_stats(update_error)
            raise
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Update stats atomically
        def update_stats(stats):
            stats["total_requests"] += 1
            current_time = time.time()
            stats["last_minute_requests"].append(current_time)
            # Clean old timestamps (older than 5 minutes)
            stats["last_minute_requests"] = [
                t for t in stats["last_minute_requests"]
                if current_time - t < 300
            ]
            
            # Track response time (keep last 100)
            stats["request_times"].append(response_time)
            if len(stats["request_times"]) > 100:
                stats["request_times"] = stats["request_times"][-100:]
            
            # Track errors (only 5xx server errors, not 4xx client errors)
            if response.status_code >= 500:
                stats["errors"] += 1
            
            logger.debug(f"Updated stats: total_requests={stats['total_requests']}, errors={stats['errors']}, response_time={response_time:.3f}s, status={response.status_code}")
        
        _update_stats(update_stats)
        
        # Log request at INFO level (visible in logs page)
        logger.info(f"{request.method} {request.url.path} - {response.status_code} - {response_time:.3f}s")
        
        # Log errors at WARNING level for visibility
        if response.status_code >= 400:
            logger.warning(f"Request error: {request.method} {request.url.path} - Status {response.status_code} - {response_time:.3f}s")
        
        return response


def _get_gunicorn_processes():
    """Find Gunicorn master and worker processes with caching."""
    current_time = time.time()
    
    with _process_enumeration_cache["lock"]:
        # Check if cache is valid
        if (_process_enumeration_cache["data"] is not None and 
            current_time - _process_enumeration_cache["timestamp"] < PROCESS_ENUMERATION_CACHE_TTL):
            return _process_enumeration_cache["data"]
        
        # Cache expired or missing - refresh it
        result = _get_gunicorn_processes_uncached()
        _process_enumeration_cache["data"] = result
        _process_enumeration_cache["timestamp"] = current_time
        return result


def _get_gunicorn_processes_uncached():
    """Find Gunicorn master and worker processes (uncached implementation)."""
    processes = []
    master_pid = None
    
    # Strategy 1: Look for process with 'gunicorn' and 'app.main:app' in cmdline
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid', 'create_time']):
        try:
            pinfo = proc.info
            cmdline = pinfo.get('cmdline', [])
            
            if not cmdline:
                continue
                
            cmdline_str = ' '.join(str(arg) for arg in cmdline).lower()
            
            # Check if this is a Gunicorn master process
            if 'gunicorn' in cmdline_str and 'app.main:app' in cmdline_str:
                master_pid = pinfo['pid']
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    # Strategy 2: If not found, look for gunicorn process with proc_name 'frl-python-api'
    if not master_pid:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid', 'create_time']):
            try:
                pinfo = proc.info
                cmdline = pinfo.get('cmdline', [])
                
                if not cmdline:
                    continue
                    
                cmdline_str = ' '.join(str(arg) for arg in cmdline).lower()
                
                if 'gunicorn' in cmdline_str:
                    # Check if it's the master (has proc_name or no gunicorn parent)
                    try:
                        parent = psutil.Process(pinfo['pid']).parent()
                        parent_cmdline = parent.cmdline() if parent else []
                        parent_str = ' '.join(str(arg) for arg in parent_cmdline).lower()
                        
                        # Master process typically doesn't have a gunicorn parent
                        if 'gunicorn' not in parent_str:
                            master_pid = pinfo['pid']
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        # If we can't check parent, assume it might be master
                        if 'frl-python-api' in cmdline_str or 'gunicorn_config' in cmdline_str:
                            master_pid = pinfo['pid']
                            break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    
    # Get worker processes from master
    if master_pid:
        try:
            master_proc = psutil.Process(master_pid)
            # Get all child processes (workers)
            for child in master_proc.children(recursive=False):
                try:
                    create_time = child.create_time()
                    mem_info = child.memory_info()
                    
                    processes.append({
                        "pid": child.pid,
                        "cpu_percent": 0,  # Will be updated in get_workers
                        "memory_mb": round(mem_info.rss / 1024 / 1024, 2),
                        "uptime_seconds": int(time.time() - create_time),
                        "status": child.status()
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return processes, master_pid


def _generate_log_hash(timestamp: str, message: str, module: Optional[str] = None) -> str:
    """Generate a hash identifier for a log entry.
    
    Uses SHA256 hash of timestamp + message (and module if available) to create
    a unique identifier for log entries.
    
    Args:
        timestamp: Log timestamp string
        message: Log message string
        module: Optional module name
        
    Returns:
        Hex digest of the hash (64 characters)
    """
    # Combine timestamp and message for hash
    hash_input = f"{timestamp}|{message}"
    if module:
        hash_input = f"{timestamp}|{module}|{message}"
    
    # Generate SHA256 hash
    hash_obj = hashlib.sha256(hash_input.encode('utf-8'))
    return hash_obj.hexdigest()


def _parse_log_line(line: str) -> Dict[str, str]:
    """Parse a log line into components."""
    # Expected format: "2024-01-01 12:00:00 - app.main - INFO - message"
    parts = line.split(' - ', 3)
    if len(parts) >= 4:
        return {
            "timestamp": parts[0],
            "module": parts[1],
            "level": parts[2],
            "message": parts[3]
        }
    elif len(parts) >= 2:
        return {
            "timestamp": parts[0] if parts[0] else "",
            "level": "INFO",
            "message": ' - '.join(parts[1:])
        }
    else:
        return {
            "timestamp": "",
            "level": "INFO",
            "message": line
        }


def _extract_log_level(line: str) -> str:
    """Extract log level from journalctl output or log line."""
    line_upper = line.upper()
    if "ERROR" in line_upper or "ERR" in line_upper:
        return "ERROR"
    elif "WARNING" in line_upper or "WARN" in line_upper:
        return "WARNING"
    elif "INFO" in line_upper:
        return "INFO"
    elif "DEBUG" in line_upper:
        return "DEBUG"
    return "INFO"


def _extract_journalctl_log_level(line: str) -> str:
    """Extract log level from journalctl structured format.
    
    Uses a three-step approach:
    1. Check for HTTP access logs with 2xx status codes (returns INFO)
    2. Parse structured journalctl format (TIMESTAMP LEVEL PRIORITY HOSTNAME SERVICE[PID]: MESSAGE)
    3. Fall back to keyword search if structured parsing fails
    
    Args:
        line: Log line from journalctl output
        
    Returns:
        Log level (ERROR, WARNING, INFO, DEBUG)
    """
    import re
    
    # Step 1: Check for HTTP access logs with 2xx status codes
    if 'HTTP/' in line:
        # Look for status codes like " 200", " 201", " 202", " 204" at end of line or before whitespace
        status_match = re.search(r'\s(2\d{2})\s*$', line)
        if status_match:
            return "INFO"
    
    # Step 2: Parse structured journalctl format
    # Format: TIMESTAMP LEVEL PRIORITY HOSTNAME SERVICE[PID]: MESSAGE
    parts = line.split(None, 3)  # Split into max 4 parts (timestamp, level, priority, rest)
    
    if len(parts) >= 3:
        # Check if first part looks like an ISO timestamp (contains 'T' separator)
        timestamp_part = parts[0]
        if 'T' in timestamp_part and len(timestamp_part) >= 10:
            # Second part should be the log level
            level_part = parts[1].upper()
            # Validate it's a known log level
            if level_part in ('ERROR', 'WARNING', 'INFO', 'DEBUG'):
                return level_part
    
    # Step 3: Fall back to keyword search if structured parsing fails
    return _extract_log_level(line)


def _get_cached_system_metrics():
    """Get system metrics with caching to reduce file I/O and process enumeration."""
    current_time = time.time()
    
    with _system_metrics_cache["lock"]:
        # Check if cache is valid
        if (_system_metrics_cache["data"] is not None and 
            current_time - _system_metrics_cache["timestamp"] < SYSTEM_METRICS_CACHE_TTL):
            return _system_metrics_cache["data"]
        
        # Cache expired or missing - refresh it
        # Get active workers
        workers, _ = _get_gunicorn_processes()
        active_workers = len([w for w in workers if w.get('status') == 'running'])
        
        # Get system CPU and memory usage
        # For first call, use small interval to establish measurement
        # For subsequent calls, use cached value (interval=0)
        if not _system_metrics_cache["cpu_baseline_set"]:
            # First call: establish baseline with small measurement
            psutil.cpu_percent(interval=None)  # Reset internal counter
            cpu_percent = psutil.cpu_percent(interval=0.1)  # Measure over 0.1s
            _system_metrics_cache["cpu_baseline_set"] = True
        else:
            # Subsequent calls: use cached value (non-blocking)
            cpu_percent = psutil.cpu_percent(interval=0)
        cpu_count = psutil.cpu_count()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Cache the metrics
        _system_metrics_cache["data"] = {
            "active_workers": active_workers,
            "cpu_percent": cpu_percent,
            "cpu_count": cpu_count,
            "mem": mem,
            "disk": disk
        }
        _system_metrics_cache["timestamp"] = current_time
        
        return _system_metrics_cache["data"]


@router.get("/workers", response_class=JSONResponse)
async def get_workers():
    """Get Gunicorn worker process information."""
    try:
        workers, master_pid = _get_gunicorn_processes()
        
        # Update CPU percentages (non-blocking)
        for worker in workers:
            try:
                proc = psutil.Process(worker['pid'])
                # Establish baseline (non-blocking)
                proc.cpu_percent(interval=None)
                # Get cached CPU percentage (non-blocking)
                worker['cpu_percent'] = proc.cpu_percent(interval=0)
                mem_info = proc.memory_info()
                worker['memory_mb'] = round(mem_info.rss / 1024 / 1024, 2)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                worker['status'] = 'dead'
        
        return {
            "master_pid": master_pid,
            "total_workers": len(workers),
            "workers": workers
        }
    except Exception as e:
        logger.error(f"Error getting worker info: {e}")
        return {
            "master_pid": None,
            "total_workers": 0,
            "workers": [],
            "error": str(e)
        }


@router.get("/stats", response_class=JSONResponse)
async def get_stats():
    """Get request statistics and performance metrics."""
    try:
        # Load stats from shared file
        stats = _load_stats()
        logger.debug(f"Loaded stats: total_requests={stats.get('total_requests', 0)}, errors={stats.get('errors', 0)}, request_times_count={len(stats.get('request_times', []))}, last_minute_count={len(stats.get('last_minute_requests', []))}")
        current_time = time.time()
        
        # Clean old request times periodically (every 10 requests, not every request)
        # Use modulo on request count to determine when to clean
        should_clean = stats.get("total_requests", 0) % 10 == 0
        if should_clean:
            original_count = len(stats["last_minute_requests"])
            stats["last_minute_requests"] = [
                t for t in stats["last_minute_requests"]
                if current_time - t < 300
            ]
            # Only save if cleaning actually removed items
            if len(stats["last_minute_requests"]) < original_count:
                _save_stats(stats)
        
        # Calculate average response time
        avg_response_time = 0
        if stats["request_times"]:
            recent_times = stats["request_times"][-100:]  # Last 100 requests
            avg_response_time = sum(recent_times) / len(recent_times) if recent_times else 0
        
        # Calculate error rate
        total_requests = stats["total_requests"]
        error_rate = stats["errors"] / total_requests if total_requests > 0 else 0
        
        # Get cached system metrics (reduces file I/O and process enumeration)
        cached_metrics = _get_cached_system_metrics()
        active_workers = cached_metrics["active_workers"]
        cpu_percent = cached_metrics["cpu_percent"]
        cpu_count = cached_metrics["cpu_count"]
        mem = cached_metrics["mem"]
        disk = cached_metrics["disk"]
        
        # Calculate average requests per minute (based on last 5 minutes)
        requests_per_minute = round(len(stats["last_minute_requests"]) / 5, 2) if stats["last_minute_requests"] else 0
        
        result = {
            "total_requests": total_requests,
            "errors": stats["errors"],
            "requests_per_minute": requests_per_minute,
            "average_response_time_ms": round(avg_response_time * 1000, 2),
            "error_rate": round(error_rate, 4),
            "active_workers": active_workers,
            "uptime_seconds": int(current_time - stats["start_time"]),
            "system": {
                "cpu_percent": round(cpu_percent, 2),
                "cpu_count": cpu_count,
                "memory_percent": round(mem.percent, 2),
                "memory_total_gb": round(mem.total / 1024 / 1024 / 1024, 2),
                "memory_used_gb": round(mem.used / 1024 / 1024 / 1024, 2),
                "memory_available_gb": round(mem.available / 1024 / 1024 / 1024, 2),
                "disk_percent": round(disk.percent, 2),
                "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 2)
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Add diagnostic info only in development mode
        if os.getenv("ENVIRONMENT", "production").lower() == "development":
            stats_file_exists = STATS_FILE.exists()
            stats_file_size = STATS_FILE.stat().st_size if stats_file_exists else 0
            result["_diagnostic"] = {
                "stats_file_exists": stats_file_exists,
                "stats_file_path": str(STATS_FILE),
                "stats_file_size": stats_file_size,
                "raw_total_requests": stats.get("total_requests", 0),
                "raw_errors": stats.get("errors", 0),
                "raw_request_times_count": len(stats.get("request_times", [])),
                "raw_last_minute_count": len(stats.get("last_minute_requests", []))
            }
        
        logger.info(f"Stats response: total_requests={total_requests}")
        return result
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {
            "error": str(e),
            "total_requests": 0,
            "requests_per_minute": 0,
            "average_response_time_ms": 0,
            "error_rate": 0,
            "active_workers": 0,
            "system": {
                "cpu_percent": 0,
                "cpu_count": 0,
                "memory_percent": 0,
                "memory_total_gb": 0,
                "memory_used_gb": 0,
                "memory_available_gb": 0
            }
        }


@router.get("/dashboard", response_class=JSONResponse)
async def get_dashboard():
    """Get dashboard data (combined stats and workers)."""
    try:
        # Get stats and workers data
        stats_data = await get_stats()
        workers_data = await get_workers()
        
        return {
            "stats": stats_data,
            "workers": workers_data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return {
            "error": str(e),
            "stats": {
                "error": str(e),
                "total_requests": 0,
                "requests_per_minute": 0,
                "average_response_time_ms": 0,
                "error_rate": 0,
                "active_workers": 0,
                "uptime_seconds": 0,
                "system": {
                    "cpu_percent": 0,
                    "cpu_count": 0,
                    "memory_percent": 0,
                    "memory_total_gb": 0,
                    "memory_used_gb": 0,
                    "memory_available_gb": 0
                }
            },
            "workers": {
                "error": str(e),
                "master_pid": None,
                "total_workers": 0,
                "workers": []
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


@router.get("/worker/{pid}", response_class=JSONResponse)
async def get_worker_details(pid: int):
    """Get detailed information about a specific worker process."""
    try:
        proc = psutil.Process(pid)
        
        # Basic process info
        proc_info = {
            "pid": pid,
            "name": proc.name(),
            "status": proc.status(),
            "create_time": proc.create_time(),
            "uptime_seconds": int(time.time() - proc.create_time()),
            "cmdline": proc.cmdline(),
        }
        
        # CPU info
        try:
            cpu_times = proc.cpu_times()
            proc_info["cpu_times"] = {
                "user": round(cpu_times.user, 2),
                "system": round(cpu_times.system, 2),
                "children_user": round(cpu_times.children_user, 2) if hasattr(cpu_times, 'children_user') else 0,
                "children_system": round(cpu_times.children_system, 2) if hasattr(cpu_times, 'children_system') else 0,
            }
            proc_info["cpu_percent"] = proc.cpu_percent(interval=0.1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_info["cpu_times"] = None
            proc_info["cpu_percent"] = 0
        
        # Memory info
        try:
            mem_info = proc.memory_info()
            mem_full = proc.memory_full_info() if hasattr(proc, 'memory_full_info') else None
            proc_info["memory"] = {
                "rss_mb": round(mem_info.rss / 1024 / 1024, 2),
                "vms_mb": round(mem_info.vms / 1024 / 1024, 2),
            }
            if mem_full:
                proc_info["memory"]["shared_mb"] = round(mem_full.shared / 1024 / 1024, 2) if hasattr(mem_full, 'shared') else 0
                proc_info["memory"]["text_mb"] = round(mem_full.text / 1024 / 1024, 2) if hasattr(mem_full, 'text') else 0
                proc_info["memory"]["data_mb"] = round(mem_full.data / 1024 / 1024, 2) if hasattr(mem_full, 'data') else 0
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_info["memory"] = None
        
        # Child processes
        try:
            children = proc.children(recursive=False)
            proc_info["children"] = []
            for child in children:
                try:
                    proc_info["children"].append({
                        "pid": child.pid,
                        "name": child.name(),
                        "status": child.status(),
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_info["children"] = []
        
        # Threads
        try:
            threads = proc.threads()
            proc_info["threads"] = [
                {
                    "id": t.id,
                    "user_time": round(t.user_time, 2) if hasattr(t, 'user_time') else 0,
                    "system_time": round(t.system_time, 2) if hasattr(t, 'system_time') else 0,
                }
                for t in threads
            ]
            proc_info["num_threads"] = len(threads)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_info["threads"] = []
            proc_info["num_threads"] = 0
        
        # Open files
        try:
            open_files = proc.open_files()
            proc_info["open_files"] = [
                {
                    "path": f.path,
                    "fd": f.fd if hasattr(f, 'fd') else None,
                }
                for f in open_files[:50]  # Limit to first 50
            ]
            proc_info["num_open_files"] = len(open_files)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_info["open_files"] = []
            proc_info["num_open_files"] = 0
        
        # Network connections
        try:
            connections = proc.connections(kind='inet')
            proc_info["connections"] = [
                {
                    "fd": c.fd if hasattr(c, 'fd') and c.fd else None,
                    "family": str(c.family),
                    "type": str(c.type),
                    "laddr": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else None,
                    "raddr": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else None,
                    "status": c.status if hasattr(c, 'status') else None,
                }
                for c in connections[:50]  # Limit to first 50
            ]
            proc_info["num_connections"] = len(connections)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_info["connections"] = []
            proc_info["num_connections"] = 0
        
        # I/O statistics
        try:
            io_counters = proc.io_counters()
            proc_info["io"] = {
                "read_count": io_counters.read_count,
                "write_count": io_counters.write_count,
                "read_bytes_mb": round(io_counters.read_bytes / 1024 / 1024, 2),
                "write_bytes_mb": round(io_counters.write_bytes / 1024 / 1024, 2),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_info["io"] = None
        
        return proc_info
    except psutil.NoSuchProcess:
        return {
            "error": f"Process {pid} not found",
            "pid": pid
        }
    except psutil.AccessDenied:
        return {
            "error": f"Access denied to process {pid}",
            "pid": pid
        }
    except Exception as e:
        logger.error(f"Error getting worker details: {e}")
        return {
            "error": str(e),
            "pid": pid
        }


@router.get("/health", response_class=JSONResponse)
async def get_health():
    """Get system health status."""
    try:
        # Check database connectivity
        db_healthy = False
        try:
            db.fetch_one("SELECT 1")
            db_healthy = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        # Check worker availability
        workers, master_pid = _get_gunicorn_processes()
        workers_healthy = len(workers) > 0 and master_pid is not None
        
        overall_status = "healthy" if (db_healthy and workers_healthy) else "degraded"
        
        return {
            "status": overall_status,
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "connected": db_healthy
            },
            "workers": {
                "status": "healthy" if workers_healthy else "unhealthy",
                "count": len(workers),
                "master_pid": master_pid
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Error getting health: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


@router.get("/logs", response_class=JSONResponse)
async def get_logs(limit: int = 1000, level: Optional[str] = None):
    """Get application logs."""
    try:
        logs = []
        
        if USE_JOURNALCTL:
            # Verify journalctl is available
            if not os.path.exists(JOURNALCTL_PATH) or not os.access(JOURNALCTL_PATH, os.X_OK):
                return {
                    "error": f"journalctl not found at {JOURNALCTL_PATH}",
                    "logs": [],
                    "suggestion": "journalctl is required for reading systemd logs. Install systemd or set USE_JOURNALCTL=false to use file-based logging.",
                    "source": "journalctl"
                }
            
            # Read from systemd journal
            cmd = [JOURNALCTL_PATH, "-u", "frl-python-api", "-n", str(limit), "--no-pager", "-o", "short-iso"]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            # Extract log level from the line using journalctl parsing
                            extracted_level = _extract_journalctl_log_level(line)
                            
                            # Filter by level if specified
                            if level and extracted_level.upper() != level.upper():
                                continue
                            
                            logs.append({
                                "timestamp": line[:19] if len(line) > 19 else "",
                                "level": extracted_level,
                                "message": line[20:] if len(line) > 20 else line
                            })
                else:
                    # journalctl command failed
                    error_msg = result.stderr.strip() or f"journalctl returned code {result.returncode}"
                    
                    # Check for specific error types
                    error_lower = error_msg.lower()
                    if "permission denied" in error_lower or "access denied" in error_lower:
                        suggestion = "Permission denied. The application user may need to be added to systemd-journal group or run with appropriate permissions."
                    elif "no such file" in error_lower or "not found" in error_lower:
                        suggestion = "Service 'frl-python-api' may not exist or journalctl cannot find it. Verify the service name."
                    else:
                        suggestion = "Check if journalctl has permission to read logs or if the service name 'frl-python-api' is correct. Try running 'journalctl -u frl-python-api -n 10' manually."
                    
                    return {
                        "error": f"Failed to read logs from journalctl: {error_msg}",
                        "logs": [],
                        "suggestion": suggestion,
                        "source": "journalctl"
                    }
            except subprocess.TimeoutExpired:
                return {
                    "error": "journalctl command timed out after 5 seconds",
                    "logs": [],
                    "suggestion": "Log volume may be very large. Try reducing the limit parameter or check system performance.",
                    "source": "journalctl"
                }
        else:
            # Read from log file
            log_path = Path(LOG_FILE_PATH)
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Get last N lines
                    lines = lines[-limit:] if len(lines) > limit else lines
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Parse log line
                        log_entry = _parse_log_line(line)
                        if level and log_entry.get('level', '').upper() != level.upper():
                            continue
                        logs.append(log_entry)
            else:
                return {
                    "error": f"Log file not found: {LOG_FILE_PATH}",
                    "logs": [],
                    "suggestion": "Set LOG_FILE_PATH environment variable or configure logging to write to a file"
                }
        
        return {
            "logs": logs,
            "total": len(logs),
            "source": "journalctl" if USE_JOURNALCTL else LOG_FILE_PATH
        }
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return {
            "error": str(e),
            "logs": []
        }


@router.get("/worker/{pid}/logs", response_class=JSONResponse)
async def get_worker_logs(pid: int, limit: int = 1000, level: Optional[str] = None):
    """Get logs for a specific worker process."""
    try:
        logs = []
        
        # Verify process exists
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
        except psutil.NoSuchProcess:
            return {
                "error": f"Process {pid} not found",
                "logs": [],
                "pid": pid
            }
        
        if USE_JOURNALCTL:
            # Verify journalctl is available
            if not os.path.exists(JOURNALCTL_PATH) or not os.access(JOURNALCTL_PATH, os.X_OK):
                return {
                    "error": f"journalctl not found at {JOURNALCTL_PATH}",
                    "logs": [],
                    "pid": pid,
                    "suggestion": "journalctl is required for reading systemd logs. Install systemd or set USE_JOURNALCTL=false to use file-based logging.",
                    "source": "journalctl"
                }
            
            # Read from systemd journal filtered by PID
            cmd = [
                JOURNALCTL_PATH,
                "-u", "frl-python-api",
                "_PID=" + str(pid),
                "-n", str(limit),
                "--no-pager",
                "-o", "short-iso"
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            # Extract log level from the line using journalctl parsing
                            extracted_level = _extract_journalctl_log_level(line)
                            
                            # Filter by level if specified
                            if level and extracted_level.upper() != level.upper():
                                continue
                            
                            logs.append({
                                "timestamp": line[:19] if len(line) > 19 else "",
                                "level": extracted_level,
                                "message": line[20:] if len(line) > 20 else line
                            })
                else:
                    # journalctl command failed
                    error_msg = result.stderr.strip() or f"journalctl returned code {result.returncode}"
                    
                    # Check for specific error types
                    error_lower = error_msg.lower()
                    if "permission denied" in error_lower or "access denied" in error_lower:
                        suggestion = "Permission denied. The application user may need to be added to systemd-journal group or run with appropriate permissions."
                    elif "no such file" in error_lower or "not found" in error_lower:
                        suggestion = f"Service 'frl-python-api' may not exist or journalctl cannot find it. Verify the service name."
                    else:
                        suggestion = f"Check if journalctl has permission to read logs or if PID {pid} has any log entries. Try running 'journalctl -u frl-python-api _PID={pid} -n 10' manually."
                    
                    return {
                        "error": f"Failed to read logs for PID {pid} from journalctl: {error_msg}",
                        "logs": [],
                        "pid": pid,
                        "suggestion": suggestion,
                        "source": "journalctl"
                    }
            except subprocess.TimeoutExpired:
                return {
                    "error": f"journalctl command timed out after 5 seconds for PID {pid}",
                    "logs": [],
                    "pid": pid,
                    "suggestion": "Log volume may be very large. Try reducing the limit parameter or check system performance.",
                    "source": "journalctl"
                }
        else:
            # Read from log file and filter by PID
            log_path = Path(LOG_FILE_PATH)
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Get last N lines (we'll filter by PID after)
                    lines = lines[-limit*2:] if len(lines) > limit*2 else lines
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Check if line contains PID (format: "PID:12345" or "[12345]")
                        pid_str = str(pid)
                        if pid_str not in line:
                            continue
                        
                        # Parse log line
                        log_entry = _parse_log_line(line)
                        if level and log_entry.get('level', '').upper() != level.upper():
                            continue
                        
                        # Add PID info to entry
                        log_entry['pid'] = pid
                        logs.append(log_entry)
                        
                        if len(logs) >= limit:
                            break
            else:
                return {
                    "error": f"Log file not found: {LOG_FILE_PATH}",
                    "logs": [],
                    "pid": pid,
                    "suggestion": "Set LOG_FILE_PATH environment variable or use journalctl"
                }
        
        return {
            "logs": logs,
            "total": len(logs),
            "pid": pid,
            "process_name": proc_name if 'proc_name' in locals() else "unknown",
            "source": "journalctl" if USE_JOURNALCTL else LOG_FILE_PATH
        }
    except Exception as e:
        logger.error(f"Error getting worker logs: {e}")
        return {
            "error": str(e),
            "logs": [],
            "pid": pid
        }


def _extract_traceback(message: str) -> Optional[str]:
    """Extract traceback from log message if present.
    
    Looks for Python traceback patterns in the message and returns
    the traceback portion if found.
    
    Args:
        message: Full log message
        
    Returns:
        Traceback string if found, None otherwise
    """
    if not message:
        return None
    
    # Look for "Traceback (most recent call last):" pattern
    traceback_start = message.find("Traceback (most recent call last):")
    if traceback_start == -1:
        # Also check for just "Traceback:"
        traceback_start = message.find("Traceback:")
        if traceback_start == -1:
            return None
    
    # Return everything from traceback start to end
    return message[traceback_start:].strip()


def _extract_metadata_from_message(message: str) -> Dict[str, Any]:
    """Extract metadata from log message if available.
    
    Attempts to extract PID, file paths, line numbers, and other
    metadata from log messages.
    
    Args:
        message: Log message string
        
    Returns:
        Dictionary with extracted metadata fields
    """
    metadata = {}
    
    if not message:
        return metadata
    
    # Try to extract PID (common patterns: "PID:12345" or "[12345]")
    import re
    pid_match = re.search(r'(?:PID[:\s]+|\[)(\d+)(?:\]|$)', message)
    if pid_match:
        try:
            metadata['pid'] = int(pid_match.group(1))
        except ValueError:
            pass
    
    # Try to extract file path and line number (pattern: "File \"path\", line 123")
    file_match = re.search(r'File\s+"([^"]+)",\s*line\s+(\d+)', message)
    if file_match:
        metadata['file_path'] = file_match.group(1)
        try:
            metadata['line_number'] = int(file_match.group(2))
        except ValueError:
            pass
    
    return metadata


@router.get("/log/{log_hash}", response_class=JSONResponse)
async def get_log_details(log_hash: str):
    """Get detailed information for a specific log entry by hash.
    
    Searches recent logs to find the log entry matching the hash.
    Note: Since logs can rotate, this may not always find the exact log.
    
    Args:
        log_hash: SHA256 hash of the log entry (timestamp + message)
        
    Returns:
        JSON object with log details including traceback and metadata
    """
    try:
        # Search recent logs (use a larger limit to increase chances of finding the log)
        limit = 5000  # Search more logs to increase likelihood of finding the entry
        all_logs_response = await get_logs(limit=limit, level=None)
        
        if all_logs_response.get("error"):
            return {
                "error": all_logs_response.get("error"),
                "log_hash": log_hash
            }
        
        logs = all_logs_response.get("logs", [])
        
        # Find log entry matching the hash
        matching_log = None
        for log in logs:
            timestamp = log.get("timestamp", "")
            message = log.get("message", "")
            module = log.get("module")
            
            # Generate hash for this log entry
            entry_hash = _generate_log_hash(timestamp, message, module)
            
            if entry_hash == log_hash:
                matching_log = log
                break
        
        if not matching_log:
            return {
                "error": f"Log entry not found (hash: {log_hash}). The log may have rotated or the entry is no longer in recent logs.",
                "log_hash": log_hash,
                "searched_logs": len(logs)
            }
        
        # Extract traceback and metadata
        message = matching_log.get("message", "")
        traceback_text = _extract_traceback(message)
        metadata = _extract_metadata_from_message(message)
        
        # Build detailed response
        result = {
            "log_hash": log_hash,
            "timestamp": matching_log.get("timestamp", ""),
            "level": matching_log.get("level", ""),
            "message": message,
            "raw_message": message,  # For copying
            "module": matching_log.get("module"),
            "source": all_logs_response.get("source", ""),
            "metadata": metadata
        }
        
        if traceback_text:
            result["traceback"] = traceback_text
        
        # Add PID if available in the log entry itself
        if "pid" in matching_log:
            result["metadata"]["pid"] = matching_log["pid"]
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting log details: {e}")
        return {
            "error": str(e),
            "log_hash": log_hash
        }


@router.get("/login", response_class=HTMLResponse)
async def get_login_page():
    """Login page for dashboard access."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Login - FRL Python API</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .login-container {
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            padding: 40px;
            width: 100%;
            max-width: 400px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
            text-align: center;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            text-align: center;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
            font-size: 14px;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus,
        input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .btn:active {
            transform: translateY(0);
        }
        .error {
            background: #fee;
            color: #c33;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
            display: none;
        }
        .error.show {
            display: block;
        }
        .info {
            background: #e3f2fd;
            color: #1976d2;
            padding: 12px;
            border-radius: 6px;
            margin-top: 20px;
            font-size: 12px;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Dashboard Login</h1>
        <p class="subtitle">FRL Python API Monitoring</p>
        
        <div id="error-message" class="error"></div>
        
        <form id="login-form">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required autocomplete="username">
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required autocomplete="current-password">
            </div>
            
            <button type="submit" class="btn">Login</button>
        </form>
    </div>
    
    <script>
        // Immediate test - this should always appear if JavaScript is running
        console.log('[LOGIN DEBUG] ===== LOGIN PAGE SCRIPT LOADED =====');
        
        try {
            const loginForm = document.getElementById('login-form');
            console.log('[LOGIN DEBUG] Login form element found:', loginForm !== null);
            
            if (!loginForm) {
                console.error('[LOGIN DEBUG] ERROR: Login form element not found!');
            } else {
                console.log('[LOGIN DEBUG] Attaching submit event listener to login form');
                loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorDiv = document.getElementById('error-message');
            
            // Debug: Log login attempt (mask password)
            console.log('[LOGIN DEBUG] Login attempt started');
            console.log('[LOGIN DEBUG] Username:', username);
            console.log('[LOGIN DEBUG] Password: **** (masked)');
            
            // Clear previous errors
            errorDiv.classList.remove('show');
            errorDiv.textContent = '';
            
            // Create basic auth header
            const credentials = btoa(username + ':' + password);
            console.log('[LOGIN DEBUG] Credentials encoded (base64 length:', credentials.length + ')');
            
            try {
                const requestUrl = '/monitor/dashboard/page';
                const requestMethod = 'GET';
                console.log('[LOGIN DEBUG] Making fetch request:', requestMethod, requestUrl);
                
                // Test authentication by making a request to a protected HTML endpoint
                const response = await fetch(requestUrl, {
                    method: requestMethod,
                    headers: {
                        'Authorization': 'Basic ' + credentials
                    }
                });
                
                console.log('[LOGIN DEBUG] Response received');
                console.log('[LOGIN DEBUG] Response status:', response.status);
                console.log('[LOGIN DEBUG] Response statusText:', response.statusText);
                console.log('[LOGIN DEBUG] Response ok:', response.ok);
                
                if (response.ok) {
                    // Authentication successful - redirect to dashboard
                    console.log('[LOGIN DEBUG] Authentication successful');
                    // Store credentials in sessionStorage for future requests
                    sessionStorage.setItem('authCredentials', credentials);
                    console.log('[LOGIN DEBUG] Credentials stored in sessionStorage');
                    console.log('[LOGIN DEBUG] Redirecting to dashboard...');
                    window.location.href = '/monitor/dashboard/page';
                } else if (response.status === 401) {
                    // Authentication failed
                    console.log('[LOGIN DEBUG] Authentication failed: 401 Unauthorized');
                    errorDiv.textContent = 'Invalid username or password. Please try again.';
                    errorDiv.classList.add('show');
                } else {
                    console.log('[LOGIN DEBUG] Unexpected response status:', response.status);
                    errorDiv.textContent = 'An error occurred. Please try again.';
                    errorDiv.classList.add('show');
                }
            } catch (error) {
                console.error('[LOGIN DEBUG] Exception caught during login:', error);
                console.error('[LOGIN DEBUG] Error name:', error.name);
                console.error('[LOGIN DEBUG] Error message:', error.message);
                console.error('[LOGIN DEBUG] Error stack:', error.stack);
                errorDiv.textContent = 'Network error. Please check your connection and try again.';
                errorDiv.classList.add('show');
                console.error('Login error:', error);
            }
                });
            }
        } catch (error) {
            console.error('[LOGIN DEBUG] ERROR: Failed to attach login form handler:', error);
            console.error('[LOGIN DEBUG] Error details:', error.name, error.message, error.stack);
        }
        
        // Auto-focus username field
        try {
            const usernameField = document.getElementById('username');
            if (usernameField) {
                usernameField.focus();
            } else {
                console.warn('[LOGIN DEBUG] Username field not found for auto-focus');
            }
        } catch (error) {
            console.error('[LOGIN DEBUG] ERROR: Failed to focus username field:', error);
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/logout", response_class=HTMLResponse)
async def get_logout_page():
    """Logout page that clears session and redirects to login."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Logout - FRL Python API</title>
</head>
<body>
    <script>
        // Clear sessionStorage
        sessionStorage.removeItem('authCredentials');
        // Redirect to login page
        window.location.href = '/monitor/login';
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/dashboard/page", response_class=HTMLResponse)
async def get_dashboard_page(request: Request):
    """HTML dashboard for monitoring Gunicorn workers."""
    username, redirect = check_auth_for_html(request)
    if redirect:
        return redirect
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gunicorn Worker Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 {
            color: #2c3e50;
            font-size: 24px;
        }
        .refresh-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            color: #666;
            font-size: 14px;
        }
        .refresh-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #4CAF50;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
        }
        .stat-unit {
            font-size: 14px;
            color: #999;
            font-weight: normal;
        }
        .workers-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .workers-section h2 {
            margin-bottom: 20px;
            color: #2c3e50;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            text-align: left;
            padding: 12px;
            background: #f8f9fa;
            color: #666;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            border-bottom: 2px solid #e0e0e0;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-running {
            background: #d4edda;
            color: #155724;
        }
        .status-idle {
            background: #fff3cd;
            color: #856404;
        }
        .status-dead {
            background: #f8d7da;
            color: #721c24;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .uptime {
            color: #666;
            font-size: 12px;
        }
        .system-metrics {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .system-metrics h2 {
            color: #2c3e50;
            font-size: 18px;
            margin-bottom: 15px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .metric-item {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .metric-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            background: #4CAF50;
            transition: width 0.9s ease;
        }
        .progress-fill.warning {
            background: #ff9800;
        }
        .progress-fill.danger {
            background: #f44336;
        }
        .nav-menu {
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .nav-menu ul {
            list-style: none;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin: 0;
            padding: 0;
        }
        .nav-menu li {
            margin: 0;
        }
        .nav-menu a {
            color: #2c3e50;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 4px;
            transition: background-color 0.2s;
            display: inline-block;
        }
        .nav-menu a:hover {
            background-color: #f0f0f0;
        }
        .nav-menu a.active {
            background-color: #2c3e50;
            color: white;
        }
        .worker-link {
            color: #2c3e50;
            text-decoration: none;
            font-weight: 600;
        }
        .worker-link:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <nav class="nav-menu">
            <ul>
                <li><a href="/monitor/dashboard/page" class="active">Dashboard</a></li>
                <li><a href="/monitor/health/page">Health</a></li>
                <li><a href="/monitor/logs/page">Logs</a></li>
                <li><a href="/monitor/logout">Logout</a></li>
            </ul>
        </nav>
        
        <div class="system-metrics" id="system-metrics">
            <h2>System Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-label">CPU Usage</div>
                    <div class="metric-value" id="cpu-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="cpu-progress" style="width: 0%"></div>
                    </div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Memory Usage</div>
                    <div class="metric-value" id="memory-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="memory-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="memory-details">-</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Disk Usage</div>
                    <div class="metric-value" id="disk-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="disk-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="disk-details">-</div>
                </div>
            </div>
        </div>
        
        <header>
            <h1>Gunicorn Worker Monitor</h1>
            <div class="refresh-indicator">
                <div class="refresh-dot"></div>
                <span>Auto-refreshing every 0.5 seconds</span>
            </div>
        </header>
        
        <div id="error-container"></div>
        
        <div class="stats-grid" id="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Requests</div>
                <div class="stat-value" id="total-requests">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Requests/Min</div>
                <div class="stat-value" id="requests-per-minute">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Response Time</div>
                <div class="stat-value" id="avg-response-time">-<span class="stat-unit"> ms</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Error Rate</div>
                <div class="stat-value" id="error-rate">-<span class="stat-unit">%</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Workers</div>
                <div class="stat-value" id="active-workers">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Uptime</div>
                <div class="stat-value" id="uptime">-</div>
            </div>
        </div>
        
        <div class="workers-section">
            <h2>Worker Processes</h2>
            <div id="workers-container" class="loading">Loading workers...</div>
        </div>
    </div>
    
    <script>
        function formatUptime(seconds) {
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = seconds % 60;
            
            if (days > 0) return `${days}d ${hours}h ${minutes}m`;
            if (hours > 0) return `${hours}h ${minutes}m`;
            if (minutes > 0) return `${minutes}m ${secs}s`;
            return `${secs}s`;
        }
        
        function formatMemory(mb) {
            if (mb >= 1024) return (mb / 1024).toFixed(2) + ' GB';
            return mb.toFixed(2) + ' MB';
        }
        
        async function fetchDashboard() {
            try {
                const response = await fetch('/monitor/dashboard');
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('error-container').innerHTML = 
                        '<div class="error">Error: ' + data.error + '</div>';
                    return;
                }
                
                const stats = data.stats || {};
                const workers = data.workers || {};
                
                // Handle stats data
                if (stats.error) {
                    document.getElementById('error-container').innerHTML = 
                        '<div class="error">Error: ' + stats.error + '</div>';
                    return;
                }
                
                document.getElementById('total-requests').textContent = stats.total_requests.toLocaleString();
                document.getElementById('requests-per-minute').textContent = stats.requests_per_minute;
                document.getElementById('avg-response-time').innerHTML = 
                    stats.average_response_time_ms.toFixed(2) + '<span class="stat-unit"> ms</span>';
                document.getElementById('error-rate').innerHTML = 
                    (stats.error_rate * 100).toFixed(2) + '<span class="stat-unit">%</span>';
                document.getElementById('active-workers').textContent = stats.active_workers;
                document.getElementById('uptime').textContent = formatUptime(stats.uptime_seconds);
                
                // Update system metrics
                if (stats.system) {
                    const cpuPercent = stats.system.cpu_percent;
                    const memPercent = stats.system.memory_percent;
                    
                    document.getElementById('cpu-percent').textContent = cpuPercent.toFixed(1) + '%';
                    const cpuProgress = document.getElementById('cpu-progress');
                    cpuProgress.style.width = cpuPercent + '%';
                    cpuProgress.className = 'progress-fill' + 
                        (cpuPercent > 80 ? ' danger' : cpuPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-percent').textContent = memPercent.toFixed(1) + '%';
                    const memProgress = document.getElementById('memory-progress');
                    memProgress.style.width = memPercent + '%';
                    memProgress.className = 'progress-fill' + 
                        (memPercent > 80 ? ' danger' : memPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-details').textContent = 
                        stats.system.memory_used_gb.toFixed(2) + ' GB / ' + 
                        stats.system.memory_total_gb.toFixed(2) + ' GB';
                    
                    const diskPercent = stats.system.disk_percent;
                    document.getElementById('disk-percent').textContent = diskPercent.toFixed(1) + '%';
                    const diskProgress = document.getElementById('disk-progress');
                    diskProgress.style.width = diskPercent + '%';
                    diskProgress.className = 'progress-fill' + 
                        (diskPercent > 80 ? ' danger' : diskPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('disk-details').textContent = 
                        stats.system.disk_used_gb.toFixed(2) + ' GB / ' + 
                        stats.system.disk_total_gb.toFixed(2) + ' GB';
                }
                
                // Handle workers data
                if (workers.error) {
                    document.getElementById('workers-container').innerHTML = 
                        '<div class="error">Error: ' + workers.error + '</div>';
                    return;
                }
                
                if (!workers.workers || workers.workers.length === 0) {
                    document.getElementById('workers-container').innerHTML = 
                        '<div class="loading">No workers found. Make sure Gunicorn is running.</div>';
                    return;
                }
                
                let html = '<table><thead><tr>';
                html += '<th>PID</th>';
                html += '<th>CPU %</th>';
                html += '<th>Memory</th>';
                html += '<th>Uptime</th>';
                html += '<th>Status</th>';
                html += '</tr></thead><tbody>';
                
                workers.workers.forEach(worker => {
                    html += '<tr>';
                    html += '<td><a href="/monitor/worker/' + worker.pid + '/page" class="worker-link">' + worker.pid + '</a></td>';
                    html += '<td>' + worker.cpu_percent.toFixed(2) + '%</td>';
                    html += '<td>' + formatMemory(worker.memory_mb) + '</td>';
                    html += '<td class="uptime">' + formatUptime(worker.uptime_seconds) + '</td>';
                    html += '<td><span class="status-badge status-' + worker.status + '">' + worker.status + '</span></td>';
                    html += '</tr>';
                });
                
                html += '</tbody></table>';
                html += '<div style="margin-top: 10px; color: #666; font-size: 12px;">';
                html += 'Master PID: ' + (workers.master_pid || 'N/A') + ' | Total Workers: ' + workers.total_workers;
                html += '</div>';
                
                document.getElementById('workers-container').innerHTML = html;
                document.getElementById('error-container').innerHTML = '';
            } catch (error) {
                document.getElementById('error-container').innerHTML = 
                    '<div class="error">Error fetching dashboard: ' + error.message + '</div>';
            }
        }
        
        async function refresh() {
            await fetchDashboard();
        }
        
        // Initial load
        refresh();
        
        // Auto-refresh every 0.5 seconds
        setInterval(refresh, 500);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/worker/{pid}/page", response_class=HTMLResponse)
async def get_worker_detail_page(pid: int, request: Request):
    """HTML page for viewing detailed worker process information."""
    username, redirect = check_auth_for_html(request)
    if redirect:
        return redirect
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Worker {pid} Details - Gunicorn Monitor</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #2c3e50;
            text-decoration: none;
            font-weight: 500;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
        .detail-section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .detail-section h2 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 20px;
        }}
        .detail-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}
        .detail-item {{
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .detail-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .detail-value {{
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th {{
            text-align: left;
            padding: 10px;
            background: #f8f9fa;
            color: #666;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            border-bottom: 2px solid #e0e0e0;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
            font-size: 14px;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: #666;
        }}
        .error {{
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
        }}
        .nav-menu {{
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .nav-menu ul {{
            list-style: none;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin: 0;
            padding: 0;
        }}
        .nav-menu li {{
            margin: 0;
        }}
        .nav-menu a {{
            color: #2c3e50;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 4px;
            transition: background-color 0.2s;
            display: inline-block;
        }}
        .nav-menu a:hover {{
            background-color: #f0f0f0;
        }}
        .nav-menu a.active {{
            background-color: #2c3e50;
            color: white;
        }}
        .system-metrics {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .system-metrics h2 {{
            color: #2c3e50;
            font-size: 18px;
            margin-bottom: 15px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        .metric-item {{
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }}
        .progress-fill {{
            height: 100%;
            background: #4CAF50;
            transition: width 0.9s ease;
        }}
        .progress-fill.warning {{
            background: #ff9800;
        }}
        .progress-fill.danger {{
            background: #f44336;
        }}
    </style>
</head>
<body>
    <div class="container">
        <nav class="nav-menu">
            <ul>
                <li><a href="/monitor/dashboard/page">Dashboard</a></li>
                <li><a href="/monitor/health/page">Health</a></li>
                <li><a href="/monitor/logs/page">Logs</a></li>
                <li><a href="/monitor/logout">Logout</a></li>
            </ul>
        </nav>
        
        <div class="system-metrics" id="system-metrics">
            <h2>System Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-label">CPU Usage</div>
                    <div class="metric-value" id="cpu-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="cpu-progress" style="width: 0%"></div>
                    </div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Memory Usage</div>
                    <div class="metric-value" id="memory-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="memory-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="memory-details">-</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Disk Usage</div>
                    <div class="metric-value" id="disk-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="disk-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="disk-details">-</div>
                </div>
            </div>
        </div>
        
        <a href="/monitor/dashboard/page" class="back-link">← Back to Dashboard</a>
        
        <div id="worker-details" class="loading">Loading worker details...</div>
    </div>
    
    <script>
        async function loadWorkerDetails() {{
            try {{
                const response = await fetch('/monitor/worker/{pid}');
                const data = await response.json();
                
                if (data.error) {{
                    document.getElementById('worker-details').innerHTML = 
                        '<div class="error">Error: ' + data.error + '</div>';
                    return;
                }}
                
                let html = '';
                
                // Overview Section
                html += '<div class="detail-section">';
                html += '<h2>Overview</h2>';
                html += '<div class="detail-grid">';
                html += '<div class="detail-item"><div class="detail-label">PID</div><div class="detail-value">' + data.pid + '</div></div>';
                html += '<div class="detail-item"><div class="detail-label">Name</div><div class="detail-value">' + (data.name || 'N/A') + '</div></div>';
                html += '<div class="detail-item"><div class="detail-label">Status</div><div class="detail-value">' + (data.status || 'N/A') + '</div></div>';
                html += '<div class="detail-item"><div class="detail-label">Uptime</div><div class="detail-value">' + formatUptime(data.uptime_seconds || 0) + '</div></div>';
                html += '<div class="detail-item"><div class="detail-label">CPU %</div><div class="detail-value">' + (data.cpu_percent || 0).toFixed(2) + '%</div></div>';
                html += '<div class="detail-item"><div class="detail-label">Threads</div><div class="detail-value">' + (data.num_threads || 0) + '</div></div>';
                html += '<div class="detail-item"><div class="detail-label">Logs</div><div class="detail-value"><a href="/monitor/worker/' + data.pid + '/logs/page" style="color: #2c3e50; text-decoration: none; font-weight: 600;">View Logs →</a></div></div>';
                html += '</div></div>';
                
                // Memory Section
                if (data.memory) {{
                    html += '<div class="detail-section">';
                    html += '<h2>Memory</h2>';
                    html += '<div class="detail-grid">';
                    html += '<div class="detail-item"><div class="detail-label">RSS</div><div class="detail-value">' + data.memory.rss_mb.toFixed(2) + ' MB</div></div>';
                    html += '<div class="detail-item"><div class="detail-label">VMS</div><div class="detail-value">' + data.memory.vms_mb.toFixed(2) + ' MB</div></div>';
                    if (data.memory.shared_mb !== undefined) {{
                        html += '<div class="detail-item"><div class="detail-label">Shared</div><div class="detail-value">' + data.memory.shared_mb.toFixed(2) + ' MB</div></div>';
                    }}
                    html += '</div></div>';
                }}
                
                // Children Section
                if (data.children && data.children.length > 0) {{
                    html += '<div class="detail-section">';
                    html += '<h2>Child Processes (' + data.children.length + ')</h2>';
                    html += '<table><thead><tr><th>PID</th><th>Name</th><th>Status</th></tr></thead><tbody>';
                    data.children.forEach(child => {{
                        html += '<tr><td>' + child.pid + '</td><td>' + child.name + '</td><td>' + child.status + '</td></tr>';
                    }});
                    html += '</tbody></table></div>';
                }}
                
                // Threads Section
                if (data.threads && data.threads.length > 0) {{
                    html += '<div class="detail-section">';
                    html += '<h2>Threads (' + data.threads.length + ')</h2>';
                    html += '<table><thead><tr><th>Thread ID</th><th>User Time</th><th>System Time</th></tr></thead><tbody>';
                    data.threads.slice(0, 20).forEach(thread => {{
                        html += '<tr><td>' + thread.id + '</td><td>' + thread.user_time.toFixed(2) + 's</td><td>' + thread.system_time.toFixed(2) + 's</td></tr>';
                    }});
                    if (data.threads.length > 20) {{
                        html += '<tr><td colspan="3">... and ' + (data.threads.length - 20) + ' more</td></tr>';
                    }}
                    html += '</tbody></table></div>';
                }}
                
                // Connections Section
                if (data.connections && data.connections.length > 0) {{
                    html += '<div class="detail-section">';
                    html += '<h2>Network Connections (' + data.connections.length + ')</h2>';
                    html += '<table><thead><tr><th>Local Address</th><th>Remote Address</th><th>Status</th><th>Type</th></tr></thead><tbody>';
                    data.connections.forEach(conn => {{
                        html += '<tr><td>' + (conn.laddr || 'N/A') + '</td><td>' + (conn.raddr || 'N/A') + '</td><td>' + (conn.status || 'N/A') + '</td><td>' + (conn.type || 'N/A') + '</td></tr>';
                    }});
                    html += '</tbody></table></div>';
                }}
                
                // I/O Section
                if (data.io) {{
                    html += '<div class="detail-section">';
                    html += '<h2>I/O Statistics</h2>';
                    html += '<div class="detail-grid">';
                    html += '<div class="detail-item"><div class="detail-label">Read Count</div><div class="detail-value">' + data.io.read_count.toLocaleString() + '</div></div>';
                    html += '<div class="detail-item"><div class="detail-label">Write Count</div><div class="detail-value">' + data.io.write_count.toLocaleString() + '</div></div>';
                    html += '<div class="detail-item"><div class="detail-label">Read Bytes</div><div class="detail-value">' + data.io.read_bytes_mb.toFixed(2) + ' MB</div></div>';
                    html += '<div class="detail-item"><div class="detail-label">Write Bytes</div><div class="detail-value">' + data.io.write_bytes_mb.toFixed(2) + ' MB</div></div>';
                    html += '</div></div>';
                }}
                
                // Command Line Section
                if (data.cmdline && data.cmdline.length > 0) {{
                    html += '<div class="detail-section">';
                    html += '<h2>Command Line</h2>';
                    html += '<div style="background: #f8f9fa; padding: 15px; border-radius: 4px; font-family: monospace; word-break: break-all;">';
                    html += data.cmdline.join(' ');
                    html += '</div></div>';
                }}
                
                document.getElementById('worker-details').innerHTML = html;
            }} catch (error) {{
                document.getElementById('worker-details').innerHTML = 
                    '<div class="error">Error loading worker details: ' + error.message + '</div>';
            }}
        }}
        
        function formatUptime(seconds) {{
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = seconds % 60;
            
            if (days > 0) return `${{days}}d ${{hours}}h ${{minutes}}m`;
            if (hours > 0) return `${{hours}}h ${{minutes}}m`;
            if (minutes > 0) return `${{minutes}}m ${{secs}}s`;
            return `${{secs}}s`;
        }}
        
        async function fetchSystemMetrics() {{
            try {{
                const response = await fetch('/monitor/stats');
                const data = await response.json();
                
                if (data.system) {{
                    const cpuPercent = data.system.cpu_percent;
                    const memPercent = data.system.memory_percent;
                    
                    document.getElementById('cpu-percent').textContent = cpuPercent.toFixed(1) + '%';
                    const cpuProgress = document.getElementById('cpu-progress');
                    cpuProgress.style.width = cpuPercent + '%';
                    cpuProgress.className = 'progress-fill' + 
                        (cpuPercent > 80 ? ' danger' : cpuPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-percent').textContent = memPercent.toFixed(1) + '%';
                    const memProgress = document.getElementById('memory-progress');
                    memProgress.style.width = memPercent + '%';
                    memProgress.className = 'progress-fill' + 
                        (memPercent > 80 ? ' danger' : memPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-details').textContent = 
                        data.system.memory_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.memory_total_gb.toFixed(2) + ' GB';
                    
                    const diskPercent = data.system.disk_percent;
                    document.getElementById('disk-percent').textContent = diskPercent.toFixed(1) + '%';
                    const diskProgress = document.getElementById('disk-progress');
                    diskProgress.style.width = diskPercent + '%';
                    diskProgress.className = 'progress-fill' + 
                        (diskPercent > 80 ? ' danger' : diskPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('disk-details').textContent = 
                        data.system.disk_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.disk_total_gb.toFixed(2) + ' GB';
                }}
            }} catch (error) {{
                // Silently fail - don't break the page if system metrics fail
            }}
        }}
        
        // Load on page load
        fetchSystemMetrics();
        loadWorkerDetails();
        
        // Auto-refresh system metrics every 0.5 seconds (matching dashboard)
        setInterval(() => {{
            fetchSystemMetrics();
        }}, 500);
        
        // Auto-refresh worker details every 5 seconds
        setInterval(() => {{
            loadWorkerDetails();
        }}, 5000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/workers/page", response_class=HTMLResponse)
async def get_workers_page(request: Request):
    """HTML page for viewing worker processes."""
    username, redirect = check_auth_for_html(request)
    if redirect:
        return redirect
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Workers - Gunicorn Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .nav-menu {
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .nav-menu ul {
            list-style: none;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin: 0;
            padding: 0;
        }
        .nav-menu li {
            margin: 0;
        }
        .nav-menu a {
            color: #2c3e50;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 4px;
            transition: background-color 0.2s;
            display: inline-block;
        }
        .nav-menu a:hover {
            background-color: #f0f0f0;
        }
        .nav-menu a.active {
            background-color: #2c3e50;
            color: white;
        }
        .system-metrics {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .system-metrics h2 {
            color: #2c3e50;
            font-size: 18px;
            margin-bottom: 15px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .metric-item {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .metric-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            background: #4CAF50;
            transition: width 0.9s ease;
        }
        .progress-fill.warning {
            background: #ff9800;
        }
        .progress-fill.danger {
            background: #f44336;
        }
        .workers-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .workers-section h2 {
            margin-bottom: 20px;
            color: #2c3e50;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            text-align: left;
            padding: 12px;
            background: #f8f9fa;
            color: #666;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            border-bottom: 2px solid #e0e0e0;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-running {
            background: #d4edda;
            color: #155724;
        }
        .status-idle {
            background: #fff3cd;
            color: #856404;
        }
        .status-dead {
            background: #f8d7da;
            color: #721c24;
        }
        .worker-link {
            color: #2c3e50;
            text-decoration: none;
            font-weight: 600;
        }
        .worker-link:hover {
            text-decoration: underline;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .uptime {
            color: #666;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <nav class="nav-menu">
            <ul>
                <li><a href="/monitor/dashboard/page">Dashboard</a></li>
                <li><a href="/monitor/health/page">Health</a></li>
                <li><a href="/monitor/logs/page">Logs</a></li>
                <li><a href="/monitor/logout">Logout</a></li>
            </ul>
        </nav>
        
        <div class="system-metrics" id="system-metrics">
            <h2>System Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-label">CPU Usage</div>
                    <div class="metric-value" id="cpu-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="cpu-progress" style="width: 0%"></div>
                    </div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Memory Usage</div>
                    <div class="metric-value" id="memory-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="memory-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="memory-details">-</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Disk Usage</div>
                    <div class="metric-value" id="disk-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="disk-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="disk-details">-</div>
                </div>
            </div>
        </div>
        
        <div class="workers-section">
            <h2>Worker Processes</h2>
            <div id="error-container"></div>
            <div id="workers-container" class="loading">Loading workers...</div>
        </div>
    </div>
    
    <script>
        function formatUptime(seconds) {
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = seconds % 60;
            
            if (days > 0) return `${days}d ${hours}h ${minutes}m`;
            if (hours > 0) return `${hours}h ${minutes}m`;
            if (minutes > 0) return `${minutes}m ${secs}s`;
            return `${secs}s`;
        }
        
        function formatMemory(mb) {
            if (mb >= 1024) return (mb / 1024).toFixed(2) + ' GB';
            return mb.toFixed(2) + ' MB';
        }
        
        async function fetchWorkers() {
            try {
                const response = await fetch('/monitor/workers');
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('workers-container').innerHTML = 
                        '<div class="error">Error: ' + data.error + '</div>';
                    document.getElementById('error-container').innerHTML = '';
                    return;
                }
                
                if (data.workers.length === 0) {
                    document.getElementById('workers-container').innerHTML = 
                        '<div class="loading">No workers found. Make sure Gunicorn is running.</div>';
                    document.getElementById('error-container').innerHTML = '';
                    return;
                }
                
                let html = '<table><thead><tr>';
                html += '<th>PID</th>';
                html += '<th>CPU %</th>';
                html += '<th>Memory</th>';
                html += '<th>Uptime</th>';
                html += '<th>Status</th>';
                html += '</tr></thead><tbody>';
                
                data.workers.forEach(worker => {
                    html += '<tr>';
                    html += '<td><a href="/monitor/worker/' + worker.pid + '/page" class="worker-link">' + worker.pid + '</a></td>';
                    html += '<td>' + worker.cpu_percent.toFixed(2) + '%</td>';
                    html += '<td>' + formatMemory(worker.memory_mb) + '</td>';
                    html += '<td class="uptime">' + formatUptime(worker.uptime_seconds) + '</td>';
                    html += '<td><span class="status-badge status-' + worker.status + '">' + worker.status + '</span></td>';
                    html += '</tr>';
                });
                
                html += '</tbody></table>';
                html += '<div style="margin-top: 10px; color: #666; font-size: 12px;">';
                html += 'Master PID: ' + (data.master_pid || 'N/A') + ' | Total Workers: ' + data.total_workers;
                html += '</div>';
                
                document.getElementById('workers-container').innerHTML = html;
                document.getElementById('error-container').innerHTML = '';
            } catch (error) {
                document.getElementById('workers-container').innerHTML = 
                    '<div class="error">Error fetching workers: ' + error.message + '</div>';
                document.getElementById('error-container').innerHTML = '';
            }
        }
        
        async function fetchSystemMetrics() {
            try {
                const response = await fetch('/monitor/stats');
                const data = await response.json();
                
                if (data.system) {
                    const cpuPercent = data.system.cpu_percent;
                    const memPercent = data.system.memory_percent;
                    
                    document.getElementById('cpu-percent').textContent = cpuPercent.toFixed(1) + '%';
                    const cpuProgress = document.getElementById('cpu-progress');
                    cpuProgress.style.width = cpuPercent + '%';
                    cpuProgress.className = 'progress-fill' + 
                        (cpuPercent > 80 ? ' danger' : cpuPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-percent').textContent = memPercent.toFixed(1) + '%';
                    const memProgress = document.getElementById('memory-progress');
                    memProgress.style.width = memPercent + '%';
                    memProgress.className = 'progress-fill' + 
                        (memPercent > 80 ? ' danger' : memPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-details').textContent = 
                        data.system.memory_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.memory_total_gb.toFixed(2) + ' GB';
                    
                    const diskPercent = data.system.disk_percent;
                    document.getElementById('disk-percent').textContent = diskPercent.toFixed(1) + '%';
                    const diskProgress = document.getElementById('disk-progress');
                    diskProgress.style.width = diskPercent + '%';
                    diskProgress.className = 'progress-fill' + 
                        (diskPercent > 80 ? ' danger' : diskPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('disk-details').textContent = 
                        data.system.disk_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.disk_total_gb.toFixed(2) + ' GB';
                }
            } catch (error) {
                // Silently fail - don't break the page if system metrics fail
            }
        }
        
        // Initial load
        fetchSystemMetrics();
        fetchWorkers();
        
        // Auto-refresh system metrics every 0.5 seconds (matching dashboard)
        setInterval(() => {
            fetchSystemMetrics();
        }, 500);
        
        // Auto-refresh workers every 5 seconds
        setInterval(() => {
            fetchWorkers();
        }, 5000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/stats/page", response_class=HTMLResponse)
async def get_stats_page(request: Request):
    """HTML page for viewing request statistics."""
    username, redirect = check_auth_for_html(request)
    if redirect:
        return redirect
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stats - Gunicorn Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .nav-menu {
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .nav-menu ul {
            list-style: none;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin: 0;
            padding: 0;
        }
        .nav-menu li {
            margin: 0;
        }
        .nav-menu a {
            color: #2c3e50;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 4px;
            transition: background-color 0.2s;
            display: inline-block;
        }
        .nav-menu a:hover {
            background-color: #f0f0f0;
        }
        .nav-menu a.active {
            background-color: #2c3e50;
            color: white;
        }
        .system-metrics {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .system-metrics h2 {
            color: #2c3e50;
            font-size: 18px;
            margin-bottom: 15px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .metric-item {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .metric-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            background: #4CAF50;
            transition: width 0.3s ease;
        }
        .progress-fill.warning {
            background: #ff9800;
        }
        .progress-fill.danger {
            background: #f44336;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
        }
        .stat-unit {
            font-size: 14px;
            color: #999;
            font-weight: normal;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <nav class="nav-menu">
            <ul>
                <li><a href="/monitor/dashboard/page">Dashboard</a></li>
                <li><a href="/monitor/health/page">Health</a></li>
                <li><a href="/monitor/logs/page">Logs</a></li>
                <li><a href="/monitor/logout">Logout</a></li>
            </ul>
        </nav>
        
        <div id="error-container"></div>
        
        <div class="system-metrics" id="system-metrics">
            <h2>System Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-label">CPU Usage</div>
                    <div class="metric-value" id="cpu-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="cpu-progress" style="width: 0%"></div>
                    </div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Memory Usage</div>
                    <div class="metric-value" id="memory-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="memory-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="memory-details">-</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Disk Usage</div>
                    <div class="metric-value" id="disk-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="disk-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="disk-details">-</div>
                </div>
            </div>
        </div>
        
        <div class="stats-grid" id="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Requests</div>
                <div class="stat-value" id="total-requests">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Requests/Min</div>
                <div class="stat-value" id="requests-per-minute">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Response Time</div>
                <div class="stat-value" id="avg-response-time">-<span class="stat-unit"> ms</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Error Rate</div>
                <div class="stat-value" id="error-rate">-<span class="stat-unit">%</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Workers</div>
                <div class="stat-value" id="active-workers">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Uptime</div>
                <div class="stat-value" id="uptime">-</div>
            </div>
        </div>
    </div>
    
    <script>
        function formatUptime(seconds) {
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = seconds % 60;
            
            if (days > 0) return `${days}d ${hours}h ${minutes}m`;
            if (hours > 0) return `${hours}h ${minutes}m`;
            if (minutes > 0) return `${minutes}m ${secs}s`;
            return `${secs}s`;
        }
        
        async function fetchStats() {
            try {
                const response = await fetch('/monitor/stats');
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('error-container').innerHTML = 
                        '<div class="error">Error: ' + data.error + '</div>';
                    return;
                }
                
                document.getElementById('total-requests').textContent = data.total_requests.toLocaleString();
                document.getElementById('requests-per-minute').textContent = data.requests_per_minute;
                document.getElementById('avg-response-time').innerHTML = 
                    data.average_response_time_ms.toFixed(2) + '<span class="stat-unit"> ms</span>';
                document.getElementById('error-rate').innerHTML = 
                    (data.error_rate * 100).toFixed(2) + '<span class="stat-unit">%</span>';
                document.getElementById('active-workers').textContent = data.active_workers;
                document.getElementById('uptime').textContent = formatUptime(data.uptime_seconds);
                
                // Update system metrics
                if (data.system) {
                    const cpuPercent = data.system.cpu_percent;
                    const memPercent = data.system.memory_percent;
                    
                    document.getElementById('cpu-percent').textContent = cpuPercent.toFixed(1) + '%';
                    const cpuProgress = document.getElementById('cpu-progress');
                    cpuProgress.style.width = cpuPercent + '%';
                    cpuProgress.className = 'progress-fill' + 
                        (cpuPercent > 80 ? ' danger' : cpuPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-percent').textContent = memPercent.toFixed(1) + '%';
                    const memProgress = document.getElementById('memory-progress');
                    memProgress.style.width = memPercent + '%';
                    memProgress.className = 'progress-fill' + 
                        (memPercent > 80 ? ' danger' : memPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-details').textContent = 
                        data.system.memory_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.memory_total_gb.toFixed(2) + ' GB';
                    
                    const diskPercent = data.system.disk_percent;
                    document.getElementById('disk-percent').textContent = diskPercent.toFixed(1) + '%';
                    const diskProgress = document.getElementById('disk-progress');
                    diskProgress.style.width = diskPercent + '%';
                    diskProgress.className = 'progress-fill' + 
                        (diskPercent > 80 ? ' danger' : diskPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('disk-details').textContent = 
                        data.system.disk_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.disk_total_gb.toFixed(2) + ' GB';
                }
                
                document.getElementById('error-container').innerHTML = '';
            } catch (error) {
                document.getElementById('error-container').innerHTML = 
                    '<div class="error">Error fetching stats: ' + error.message + '</div>';
            }
        }
        
        // Initial load
        fetchStats();
        
        // Auto-refresh every 0.5 seconds (matching dashboard)
        setInterval(fetchStats, 500);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/health/page", response_class=HTMLResponse)
async def get_health_page(request: Request):
    """HTML page for viewing system health."""
    username, redirect = check_auth_for_html(request)
    if redirect:
        return redirect
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Health - Gunicorn Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .nav-menu {
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .nav-menu ul {
            list-style: none;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin: 0;
            padding: 0;
        }
        .nav-menu li {
            margin: 0;
        }
        .nav-menu a {
            color: #2c3e50;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 4px;
            transition: background-color 0.2s;
            display: inline-block;
        }
        .nav-menu a:hover {
            background-color: #f0f0f0;
        }
        .nav-menu a.active {
            background-color: #2c3e50;
            color: white;
        }
        .system-metrics {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .system-metrics h2 {
            color: #2c3e50;
            font-size: 18px;
            margin-bottom: 15px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .metric-item {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .metric-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            background: #4CAF50;
            transition: width 0.9s ease;
        }
        .progress-fill.warning {
            background: #ff9800;
        }
        .progress-fill.danger {
            background: #f44336;
        }
        .health-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .health-section h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 20px;
        }
        .status-banner {
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }
        .status-banner.healthy {
            background: #d4edda;
            color: #155724;
        }
        .status-banner.degraded {
            background: #fff3cd;
            color: #856404;
        }
        .status-banner.unhealthy {
            background: #f8d7da;
            color: #721c24;
        }
        .status-banner h1 {
            font-size: 32px;
            margin-bottom: 10px;
        }
        .health-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .health-card {
            padding: 20px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .health-card h3 {
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 16px;
        }
        .health-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e0e0e0;
        }
        .health-item:last-child {
            border-bottom: none;
        }
        .health-label {
            color: #666;
            font-size: 14px;
        }
        .health-value {
            color: #2c3e50;
            font-weight: 600;
            font-size: 14px;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-healthy {
            background: #d4edda;
            color: #155724;
        }
        .status-unhealthy {
            background: #f8d7da;
            color: #721c24;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <nav class="nav-menu">
            <ul>
                <li><a href="/monitor/dashboard/page">Dashboard</a></li>
                <li><a href="/monitor/health/page" class="active">Health</a></li>
                <li><a href="/monitor/logs/page">Logs</a></li>
                <li><a href="/monitor/logout">Logout</a></li>
            </ul>
        </nav>
        
        <div class="system-metrics" id="system-metrics">
            <h2>System Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-label">CPU Usage</div>
                    <div class="metric-value" id="cpu-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="cpu-progress" style="width: 0%"></div>
                    </div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Memory Usage</div>
                    <div class="metric-value" id="memory-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="memory-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="memory-details">-</div>
                </div>
            </div>
        </div>
        
        <div id="error-container"></div>
        <div id="health-container" class="loading">Loading health status...</div>
    </div>
    
    <script>
        async function fetchHealth() {
            try {
                const response = await fetch('/monitor/health');
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('health-container').innerHTML = 
                        '<div class="error">Error: ' + data.error + '</div>';
                    document.getElementById('error-container').innerHTML = '';
                    return;
                }
                
                let html = '';
                
                // Overall status banner
                const statusClass = data.status === 'healthy' ? 'healthy' : 
                                   data.status === 'degraded' ? 'degraded' : 'unhealthy';
                html += '<div class="status-banner ' + statusClass + '">';
                html += '<h1>System Status: ' + data.status.toUpperCase() + '</h1>';
                html += '<div>Last updated: ' + new Date(data.timestamp).toLocaleString() + '</div>';
                html += '</div>';
                
                // Health details
                html += '<div class="health-grid">';
                
                // Database health
                html += '<div class="health-card">';
                html += '<h3>Database</h3>';
                html += '<div class="health-item">';
                html += '<span class="health-label">Status:</span>';
                html += '<span class="health-value">';
                html += '<span class="status-badge status-' + (data.database.status === 'healthy' ? 'healthy' : 'unhealthy') + '">';
                html += data.database.status;
                html += '</span></span></div>';
                html += '<div class="health-item">';
                html += '<span class="health-label">Connected:</span>';
                html += '<span class="health-value">' + (data.database.connected ? 'Yes' : 'No') + '</span>';
                html += '</div>';
                html += '</div>';
                
                // Workers health
                html += '<div class="health-card">';
                html += '<h3>Workers</h3>';
                html += '<div class="health-item">';
                html += '<span class="health-label">Status:</span>';
                html += '<span class="health-value">';
                html += '<span class="status-badge status-' + (data.workers.status === 'healthy' ? 'healthy' : 'unhealthy') + '">';
                html += data.workers.status;
                html += '</span></span></div>';
                html += '<div class="health-item">';
                html += '<span class="health-label">Count:</span>';
                html += '<span class="health-value">' + data.workers.count + '</span>';
                html += '</div>';
                html += '<div class="health-item">';
                html += '<span class="health-label">Master PID:</span>';
                html += '<span class="health-value">' + (data.workers.master_pid || 'N/A') + '</span>';
                html += '</div>';
                html += '</div>';
                
                html += '</div>';
                
                document.getElementById('health-container').innerHTML = html;
                document.getElementById('error-container').innerHTML = '';
            } catch (error) {
                document.getElementById('health-container').innerHTML = 
                    '<div class="error">Error fetching health: ' + error.message + '</div>';
                document.getElementById('error-container').innerHTML = '';
            }
        }
        
        async function fetchSystemMetrics() {
            try {
                const response = await fetch('/monitor/stats');
                const data = await response.json();
                
                if (data.system) {
                    const cpuPercent = data.system.cpu_percent;
                    const memPercent = data.system.memory_percent;
                    
                    document.getElementById('cpu-percent').textContent = cpuPercent.toFixed(1) + '%';
                    const cpuProgress = document.getElementById('cpu-progress');
                    cpuProgress.style.width = cpuPercent + '%';
                    cpuProgress.className = 'progress-fill' + 
                        (cpuPercent > 80 ? ' danger' : cpuPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-percent').textContent = memPercent.toFixed(1) + '%';
                    const memProgress = document.getElementById('memory-progress');
                    memProgress.style.width = memPercent + '%';
                    memProgress.className = 'progress-fill' + 
                        (memPercent > 80 ? ' danger' : memPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-details').textContent = 
                        data.system.memory_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.memory_total_gb.toFixed(2) + ' GB';
                    
                    const diskPercent = data.system.disk_percent;
                    document.getElementById('disk-percent').textContent = diskPercent.toFixed(1) + '%';
                    const diskProgress = document.getElementById('disk-progress');
                    diskProgress.style.width = diskPercent + '%';
                    diskProgress.className = 'progress-fill' + 
                        (diskPercent > 80 ? ' danger' : diskPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('disk-details').textContent = 
                        data.system.disk_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.disk_total_gb.toFixed(2) + ' GB';
                }
            } catch (error) {
                // Silently fail - don't break the page if system metrics fail
            }
        }
        
        // Initial load
        fetchSystemMetrics();
        fetchHealth();
        
        // Auto-refresh system metrics every 0.5 seconds (matching dashboard)
        setInterval(() => {
            fetchSystemMetrics();
        }, 500);
        
        // Auto-refresh health every 5 seconds
        setInterval(() => {
            fetchHealth();
        }, 5000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/logs/page", response_class=HTMLResponse)
async def get_logs_page(request: Request):
    """HTML page for viewing application logs."""
    username, redirect = check_auth_for_html(request)
    if redirect:
        return redirect
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Logs - Gunicorn Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, monospace;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        .nav-menu {
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .nav-menu ul {
            list-style: none;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin: 0;
            padding: 0;
        }
        .nav-menu li {
            margin: 0;
        }
        .nav-menu a {
            color: #2c3e50;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 4px;
            transition: background-color 0.2s;
            display: inline-block;
        }
        .nav-menu a:hover {
            background-color: #f0f0f0;
        }
        .nav-menu a.active {
            background-color: #2c3e50;
            color: white;
        }
        .system-metrics {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .system-metrics h2 {
            color: #2c3e50;
            font-size: 18px;
            margin-bottom: 15px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .metric-item {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .metric-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            background: #4CAF50;
            transition: width 0.9s ease;
        }
        .progress-fill.warning {
            background: #ff9800;
        }
        .progress-fill.danger {
            background: #f44336;
        }
        .logs-controls {
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        .logs-controls label {
            font-size: 14px;
            color: #666;
        }
        .logs-controls select,
        .logs-controls input {
            padding: 6px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .logs-controls button {
            padding: 6px 16px;
            background: #2c3e50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .logs-controls button:hover {
            background: #34495e;
        }
        .logs-container {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            max-height: 80vh;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.6;
        }
        .log-entry {
            padding: 4px 0;
            border-bottom: 1px solid #333;
            word-wrap: break-word;
        }
        .log-entry:hover {
            background: #2a2a2a;
        }
        .log-timestamp {
            color: #858585;
            margin-right: 10px;
        }
        .log-entry .log-link {
            color: #ffffff;
            text-decoration: underline;
            font-weight: bold;
        }
        .log-entry .log-link:hover {
            color: #2196F3;
        }
        .log-entry .log-link:visited {
            color: #87CEEB;
        }
        .log-level {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 600;
            margin-right: 10px;
            min-width: 60px;
            text-align: center;
        }
        .log-level.ERROR {
            background: #f44336;
            color: white;
        }
        .log-level.WARNING {
            background: #ff9800;
            color: white;
        }
        .log-level.INFO {
            background: #2196F3;
            color: white;
        }
        .log-level.DEBUG {
            background: #9e9e9e;
            color: white;
        }
        .log-message {
            color: #d4d4d4;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .auto-scroll {
            margin-left: auto;
        }
        .auto-scroll input {
            margin-right: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <nav class="nav-menu">
            <ul>
                <li><a href="/monitor/dashboard/page">Dashboard</a></li>
                <li><a href="/monitor/health/page">Health</a></li>
                <li><a href="/monitor/logs/page" class="active">Logs</a></li>
            </ul>
        </nav>
        
        <div class="system-metrics" id="system-metrics">
            <h2>System Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-label">CPU Usage</div>
                    <div class="metric-value" id="cpu-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="cpu-progress" style="width: 0%"></div>
                    </div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Memory Usage</div>
                    <div class="metric-value" id="memory-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="memory-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="memory-details">-</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Disk Usage</div>
                    <div class="metric-value" id="disk-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="disk-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="disk-details">-</div>
                </div>
            </div>
        </div>
        
        <div class="logs-controls">
            <label>
                Limit:
                <select id="limit-select">
                    <option value="100">100</option>
                    <option value="500" selected>500</option>
                    <option value="1000">1000</option>
                    <option value="5000">5000</option>
                </select>
            </label>
            <label>
                Level:
                <select id="level-select" onchange="fetchLogs()">
                    <option value="">All</option>
                    <option value="ERROR">ERROR</option>
                    <option value="WARNING">WARNING</option>
                    <option value="INFO">INFO</option>
                    <option value="DEBUG">DEBUG</option>
                </select>
            </label>
            <button onclick="fetchLogs()">Refresh</button>
            <div class="auto-scroll">
                <input type="checkbox" id="auto-scroll" checked>
                <label for="auto-scroll">Auto-scroll</label>
            </div>
            <div class="auto-scroll">
                <input type="checkbox" id="auto-refresh">
                <label for="auto-refresh">Auto-refresh (5s)</label>
            </div>
        </div>
        
        <div id="error-container"></div>
        <div id="logs-container" class="logs-container loading">Loading logs...</div>
    </div>
    
    <script>
        let autoRefreshInterval = null;
        
        async function generateLogHash(timestamp, message, module) {
            // Combine timestamp and message for hash (matching Python implementation)
            let hashInput = timestamp + '|' + message;
            if (module) {
                hashInput = timestamp + '|' + module + '|' + message;
            }
            
            // Generate SHA256 hash using Web Crypto API
            const encoder = new TextEncoder();
            const data = encoder.encode(hashInput);
            const hashBuffer = await crypto.subtle.digest('SHA-256', data);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
            return hashHex;
        }
        
        async function formatLogEntryAsync(log) {
            const timestamp = log.timestamp || '';
            const level = (log.level || 'INFO').toUpperCase();
            const message = log.message || '';
            const module = log.module ? `[${log.module}]` : '';
            
            // Generate hash for this log entry
            const hash = await generateLogHash(timestamp, message, log.module || null);
            
            return `
                <div class="log-entry">
                    <span class="log-timestamp">
                        <a href="/monitor/log/${hash}/page" class="log-link">${timestamp}</a>
                    </span>
                    <span class="log-level ${level}">${level}</span>
                    ${module ? `<span style="color: #858585;">${module}</span>` : ''}
                    <span class="log-message">${escapeHtml(message)}</span>
                </div>
            `;
        }
        
        function formatLogEntry(log) {
            const timestamp = log.timestamp || '';
            const level = (log.level || 'INFO').toUpperCase();
            const message = log.message || '';
            const module = log.module ? `[${log.module}]` : '';
            
            // Generate hash synchronously using a simple approach (store hash in data attribute)
            // We'll generate the hash when the log is rendered
            const hashInput = timestamp + '|' + (module ? module.replace(/[\[\]]/g, '') + '|' : '') + message;
            let logHash = '';
            
            // Use a synchronous hash generation for immediate display
            // Store the hash input in a data attribute and generate hash asynchronously
            const hashPromise = generateLogHash(timestamp, message, log.module);
            
            return `
                <div class="log-entry" data-hash-input="${escapeHtml(hashInput)}">
                    <span class="log-timestamp">
                        <a href="#" class="log-link" data-timestamp="${escapeHtml(timestamp)}" data-message="${escapeHtml(message)}" data-module="${escapeHtml(log.module || '')}" onclick="event.preventDefault(); handleLogClick(this); return false;">${timestamp}</a>
                    </span>
                    <span class="log-level ${level}">${level}</span>
                    ${module ? `<span style="color: #858585;">${module}</span>` : ''}
                    <span class="log-message">
                        <a href="#" class="log-link" data-timestamp="${escapeHtml(timestamp)}" data-message="${escapeHtml(message)}" data-module="${escapeHtml(log.module || '')}" onclick="event.preventDefault(); handleLogClick(this); return false;">${escapeHtml(message)}</a>
                    </span>
                </div>
            `;
        }
        
        async function handleLogClick(element) {
            const timestamp = element.getAttribute('data-timestamp');
            const message = element.getAttribute('data-message');
            const module = element.getAttribute('data-module');
            
            const hash = await generateLogHash(timestamp, message, module || null);
            window.location.href = '/monitor/log/' + hash + '/page';
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        async function fetchLogs() {
            try {
                const limit = document.getElementById('limit-select').value;
                const level = document.getElementById('level-select').value;
                const params = new URLSearchParams({ limit });
                if (level) params.append('level', level);
                
                const response = await fetch('/monitor/logs?' + params, {
                    credentials: 'same-origin'
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    throw new Error('Server returned non-JSON response. Authentication may have failed.');
                }
                
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('logs-container').innerHTML = 
                        '<div class="error">Error: ' + data.error + '</div>';
                    document.getElementById('error-container').innerHTML = '';
                    return;
                }
                
                if (data.logs.length === 0) {
                    document.getElementById('logs-container').innerHTML = 
                        '<div class="loading">No logs found</div>';
                    document.getElementById('error-container').innerHTML = '';
                    return;
                }
                
                // Generate hashes and format log entries asynchronously
                const logHtmlPromises = data.logs.map(async (log) => {
                    return await formatLogEntryAsync(log);
                });
                const logHtmls = await Promise.all(logHtmlPromises);
                const html = logHtmls.join('');
                
                document.getElementById('logs-container').innerHTML = html;
                document.getElementById('error-container').innerHTML = '';
                
                // Auto-scroll to bottom if enabled
                if (document.getElementById('auto-scroll').checked) {
                    const container = document.getElementById('logs-container');
                    container.scrollTop = container.scrollHeight;
                }
            } catch (error) {
                document.getElementById('logs-container').innerHTML = 
                    '<div class="error">Error fetching logs: ' + error.message + '</div>';
                document.getElementById('error-container').innerHTML = '';
            }
        }
        
        function toggleAutoRefresh() {
            const checkbox = document.getElementById('auto-refresh');
            if (checkbox.checked) {
                autoRefreshInterval = setInterval(fetchLogs, 5000);
            } else {
                if (autoRefreshInterval) {
                    clearInterval(autoRefreshInterval);
                    autoRefreshInterval = null;
                }
            }
        }
        
        document.getElementById('auto-refresh').addEventListener('change', toggleAutoRefresh);
        
        async function fetchSystemMetrics() {
            try {
                const response = await fetch('/monitor/stats');
                const data = await response.json();
                
                if (data.system) {
                    const cpuPercent = data.system.cpu_percent;
                    const memPercent = data.system.memory_percent;
                    
                    document.getElementById('cpu-percent').textContent = cpuPercent.toFixed(1) + '%';
                    const cpuProgress = document.getElementById('cpu-progress');
                    cpuProgress.style.width = cpuPercent + '%';
                    cpuProgress.className = 'progress-fill' + 
                        (cpuPercent > 80 ? ' danger' : cpuPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-percent').textContent = memPercent.toFixed(1) + '%';
                    const memProgress = document.getElementById('memory-progress');
                    memProgress.style.width = memPercent + '%';
                    memProgress.className = 'progress-fill' + 
                        (memPercent > 80 ? ' danger' : memPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-details').textContent = 
                        data.system.memory_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.memory_total_gb.toFixed(2) + ' GB';
                    
                    const diskPercent = data.system.disk_percent;
                    document.getElementById('disk-percent').textContent = diskPercent.toFixed(1) + '%';
                    const diskProgress = document.getElementById('disk-progress');
                    diskProgress.style.width = diskPercent + '%';
                    diskProgress.className = 'progress-fill' + 
                        (diskPercent > 80 ? ' danger' : diskPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('disk-details').textContent = 
                        data.system.disk_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.disk_total_gb.toFixed(2) + ' GB';
                }
            } catch (error) {
                // Silently fail - don't break the page if system metrics fail
            }
        }
        
        // Initial load
        fetchSystemMetrics();
        fetchLogs();
        
        // Auto-refresh system metrics every 0.5 seconds (matching dashboard)
        setInterval(() => {
            fetchSystemMetrics();
        }, 500);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/log/{log_hash}/page", response_class=HTMLResponse)
async def get_log_detail_page(log_hash: str, request: Request):
    """HTML page for viewing detailed log entry information."""
    username, redirect = check_auth_for_html(request)
    if redirect:
        return redirect
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Log Details - Gunicorn Monitor</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #2c3e50;
            text-decoration: none;
            font-weight: 500;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
        .nav-menu {{
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .nav-menu ul {{
            list-style: none;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin: 0;
            padding: 0;
        }}
        .nav-menu li {{
            margin: 0;
        }}
        .nav-menu a {{
            color: #2c3e50;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 4px;
            transition: background-color 0.2s;
            display: inline-block;
        }}
        .nav-menu a:hover {{
            background-color: #f0f0f0;
        }}
        .nav-menu a.active {{
            background-color: #2c3e50;
            color: white;
        }}
        .system-metrics {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .system-metrics h2 {{
            color: #2c3e50;
            font-size: 18px;
            margin-bottom: 15px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        .metric-item {{
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }}
        .progress-fill {{
            height: 100%;
            background: #4CAF50;
            transition: width 0.9s ease;
        }}
        .progress-fill.warning {{
            background: #ff9800;
        }}
        .progress-fill.danger {{
            background: #f44336;
        }}
        .detail-section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .detail-section h2 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 20px;
        }}
        .detail-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .detail-timestamp {{
            font-size: 16px;
            color: #666;
            font-family: monospace;
        }}
        .level-badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .level-badge.ERROR {{
            background: #f44336;
            color: white;
        }}
        .level-badge.WARNING {{
            background: #ff9800;
            color: white;
        }}
        .level-badge.INFO {{
            background: #2196F3;
            color: white;
        }}
        .level-badge.DEBUG {{
            background: #9e9e9e;
            color: white;
        }}
        .detail-item {{
            margin-bottom: 20px;
        }}
        .detail-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        .detail-value {{
            font-size: 14px;
            color: #2c3e50;
            line-height: 1.6;
            word-wrap: break-word;
        }}
        .message-box {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #2c3e50;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .traceback-box {{
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-x: auto;
        }}
        .metadata-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .metadata-item {{
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .metadata-label {{
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .metadata-value {{
            font-size: 14px;
            font-weight: 600;
            color: #2c3e50;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: #666;
        }}
        .error {{
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
        }}
        .copy-button {{
            padding: 6px 12px;
            background: #2c3e50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-top: 10px;
        }}
        .copy-button:hover {{
            background: #34495e;
        }}
    </style>
</head>
<body>
    <div class="container">
        <nav class="nav-menu">
            <ul>
                <li><a href="/monitor/dashboard/page">Dashboard</a></li>
                <li><a href="/monitor/health/page">Health</a></li>
                <li><a href="/monitor/logs/page" class="active">Logs</a></li>
                <li><a href="/monitor/logout">Logout</a></li>
            </ul>
        </nav>
        
        <div class="system-metrics" id="system-metrics">
            <h2>System Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-label">CPU Usage</div>
                    <div class="metric-value" id="cpu-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="cpu-progress" style="width: 0%"></div>
                    </div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Memory Usage</div>
                    <div class="metric-value" id="memory-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="memory-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="memory-details">-</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Disk Usage</div>
                    <div class="metric-value" id="disk-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="disk-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="disk-details">-</div>
                </div>
            </div>
        </div>
        
        <a href="/monitor/logs/page" class="back-link">← Back to Logs</a>
        
        <div id="log-details" class="loading">Loading log details...</div>
    </div>
    
    <script>
        async function loadLogDetails() {{
            try {{
                const response = await fetch('/monitor/log/{log_hash}');
                
                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                }}
                
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {{
                    throw new Error('Server returned non-JSON response. Authentication may have failed.');
                }}
                
                const data = await response.json();
                
                if (data.error) {{
                    document.getElementById('log-details').innerHTML = 
                        '<div class="error">Error: ' + escapeHtml(data.error) + '</div>';
                    return;
                }}
                
                let html = '';
                
                // Header Section
                html += '<div class="detail-section">';
                html += '<div class="detail-header">';
                html += '<span class="level-badge ' + (data.level || 'INFO') + '">' + (data.level || 'INFO') + '</span>';
                html += '<span class="detail-timestamp">' + (data.timestamp || 'N/A') + '</span>';
                if (data.module) {{
                    html += '<span style="color: #666; font-size: 14px;">[' + data.module + ']</span>';
                }}
                html += '</div>';
                
                // Message Section
                html += '<div class="detail-item">';
                html += '<div class="detail-label">Message</div>';
                html += '<div class="message-box">' + escapeHtml(data.message || '') + '</div>';
                html += '</div>';
                
                // Raw Message Section
                html += '<div class="detail-item">';
                html += '<div class="detail-label">Raw Message</div>';
                html += '<div class="message-box" id="raw-message">' + escapeHtml(data.raw_message || data.message || '') + '</div>';
                html += '<button class="copy-button" onclick="copyToClipboard(\\'raw-message\\')">Copy Raw Message</button>';
                html += '</div>';
                
                // Traceback Section (if exists)
                if (data.traceback) {{
                    html += '<div class="detail-item">';
                    html += '<div class="detail-label">Traceback</div>';
                    html += '<div class="traceback-box" id="traceback-content">' + escapeHtml(data.traceback) + '</div>';
                    html += '<button class="copy-button" onclick="copyToClipboard(\\'traceback-content\\')">Copy Traceback</button>';
                    html += '</div>';
                }}
                
                // Metadata Section
                if (data.metadata && Object.keys(data.metadata).length > 0) {{
                    html += '<div class="detail-item">';
                    html += '<div class="detail-label">Metadata</div>';
                    html += '<div class="metadata-grid">';
                    for (const [key, value] of Object.entries(data.metadata)) {{
                        html += '<div class="metadata-item">';
                        html += '<div class="metadata-label">' + escapeHtml(key) + '</div>';
                        html += '<div class="metadata-value">' + escapeHtml(String(value)) + '</div>';
                        html += '</div>';
                    }}
                    html += '</div>';
                    html += '</div>';
                }}
                
                // Additional Info
                html += '<div class="detail-item">';
                html += '<div class="detail-label">Additional Information</div>';
                html += '<div class="metadata-grid">';
                if (data.source) {{
                    html += '<div class="metadata-item">';
                    html += '<div class="metadata-label">Source</div>';
                    html += '<div class="metadata-value">' + escapeHtml(data.source) + '</div>';
                    html += '</div>';
                }}
                html += '<div class="metadata-item">';
                html += '<div class="metadata-label">Log Hash</div>';
                html += '<div class="metadata-value" style="font-family: monospace; font-size: 12px;">' + escapeHtml(data.log_hash || 'N/A') + '</div>';
                html += '</div>';
                html += '</div>';
                html += '</div>';
                
                html += '</div>';
                
                document.getElementById('log-details').innerHTML = html;
            }} catch (error) {{
                document.getElementById('log-details').innerHTML = 
                    '<div class="error">Error loading log details: ' + escapeHtml(error.message) + '</div>';
            }}
        }}
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        function copyToClipboard(elementId) {{
            const element = document.getElementById(elementId);
            const text = element.textContent;
            navigator.clipboard.writeText(text).then(() => {{
                const button = event.target;
                const originalText = button.textContent;
                button.textContent = 'Copied!';
                setTimeout(() => {{
                    button.textContent = originalText;
                }}, 2000);
            }}).catch(err => {{
                console.error('Failed to copy:', err);
            }});
        }}
        
        async function fetchSystemMetrics() {{
            try {{
                const response = await fetch('/monitor/stats');
                const data = await response.json();
                
                if (data.system) {{
                    const cpuPercent = data.system.cpu_percent;
                    const memPercent = data.system.memory_percent;
                    
                    document.getElementById('cpu-percent').textContent = cpuPercent.toFixed(1) + '%';
                    const cpuProgress = document.getElementById('cpu-progress');
                    cpuProgress.style.width = cpuPercent + '%';
                    cpuProgress.className = 'progress-fill' + 
                        (cpuPercent > 80 ? ' danger' : cpuPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-percent').textContent = memPercent.toFixed(1) + '%';
                    const memProgress = document.getElementById('memory-progress');
                    memProgress.style.width = memPercent + '%';
                    memProgress.className = 'progress-fill' + 
                        (memPercent > 80 ? ' danger' : memPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-details').textContent = 
                        data.system.memory_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.memory_total_gb.toFixed(2) + ' GB';
                    
                    const diskPercent = data.system.disk_percent;
                    document.getElementById('disk-percent').textContent = diskPercent.toFixed(1) + '%';
                    const diskProgress = document.getElementById('disk-progress');
                    diskProgress.style.width = diskPercent + '%';
                    diskProgress.className = 'progress-fill' + 
                        (diskPercent > 80 ? ' danger' : diskPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('disk-details').textContent = 
                        data.system.disk_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.disk_total_gb.toFixed(2) + ' GB';
                }}
            }} catch (error) {{
                // Silently fail - don't break the page if system metrics fail
            }}
        }}
        
        // Initial load
        fetchSystemMetrics();
        loadLogDetails();
        
        // Auto-refresh system metrics every 0.5 seconds (matching dashboard)
        setInterval(() => {{
            fetchSystemMetrics();
        }}, 500);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/worker/{pid}/logs/page", response_class=HTMLResponse)
async def get_worker_logs_page(pid: int, request: Request):
    """HTML page for viewing worker-specific logs."""
    username, redirect = check_auth_for_html(request)
    if redirect:
        return redirect
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Worker {pid} Logs - Gunicorn Monitor</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, monospace;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        .nav-menu {{
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .nav-menu ul {{
            list-style: none;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin: 0;
            padding: 0;
        }}
        .nav-menu li {{
            margin: 0;
        }}
        .nav-menu a {{
            color: #2c3e50;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 4px;
            transition: background-color 0.2s;
            display: inline-block;
        }}
        .nav-menu a:hover {{
            background-color: #f0f0f0;
        }}
        .nav-menu a.active {{
            background-color: #2c3e50;
            color: white;
        }}
        .system-metrics {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .system-metrics h2 {{
            color: #2c3e50;
            font-size: 18px;
            margin-bottom: 15px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        .metric-item {{
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }}
        .progress-fill {{
            height: 100%;
            background: #4CAF50;
            transition: width 0.9s ease;
        }}
        .progress-fill.warning {{
            background: #ff9800;
        }}
        .progress-fill.danger {{
            background: #f44336;
        }}
        .worker-info {{
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .worker-info h2 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .worker-info p {{
            color: #666;
            margin: 5px 0;
        }}
        .logs-controls {{
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .logs-controls label {{
            font-size: 14px;
            color: #666;
        }}
        .logs-controls select,
        .logs-controls input {{
            padding: 6px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}
        .logs-controls button {{
            padding: 6px 16px;
            background: #2c3e50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        .logs-controls button:hover {{
            background: #34495e;
        }}
        .logs-container {{
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            max-height: 80vh;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.6;
        }}
        .log-entry {{
            padding: 4px 0;
            border-bottom: 1px solid #333;
            word-wrap: break-word;
        }}
        .log-entry:hover {{
            background: #2a2a2a;
        }}
        .log-timestamp {{
            color: #858585;
            margin-right: 10px;
        }}
        .log-level {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 600;
            margin-right: 10px;
            min-width: 60px;
            text-align: center;
        }}
        .log-level.ERROR {{
            background: #f44336;
            color: white;
        }}
        .log-level.WARNING {{
            background: #ff9800;
            color: white;
        }}
        .log-level.INFO {{
            background: #2196F3;
            color: white;
        }}
        .log-level.DEBUG {{
            background: #9e9e9e;
            color: white;
        }}
        .log-message {{
            color: #d4d4d4;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: #666;
        }}
        .error {{
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
        }}
        .auto-scroll {{
            margin-left: auto;
        }}
        .auto-scroll input {{
            margin-right: 5px;
        }}
        .back-link {{
            display: inline-block;
            color: #2c3e50;
            text-decoration: none;
            margin-bottom: 15px;
            font-weight: 500;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <nav class="nav-menu">
            <ul>
                <li><a href="/monitor/dashboard/page">Dashboard</a></li>
                <li><a href="/monitor/health/page">Health</a></li>
                <li><a href="/monitor/logs/page">Logs</a></li>
                <li><a href="/monitor/logout">Logout</a></li>
            </ul>
        </nav>
        
        <div class="system-metrics" id="system-metrics">
            <h2>System Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-label">CPU Usage</div>
                    <div class="metric-value" id="cpu-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="cpu-progress" style="width: 0%"></div>
                    </div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Memory Usage</div>
                    <div class="metric-value" id="memory-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="memory-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="memory-details">-</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Disk Usage</div>
                    <div class="metric-value" id="disk-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="disk-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="disk-details">-</div>
                </div>
            </div>
        </div>
        
        <a href="/monitor/worker/{pid}/page" class="back-link">← Back to Worker {pid} Details</a>
        
        <div class="worker-info" id="worker-info">
            <h2>Worker Process {pid}</h2>
            <p id="process-info">Loading process information...</p>
        </div>
        
        <div class="logs-controls">
            <label>
                Limit:
                <select id="limit-select">
                    <option value="100">100</option>
                    <option value="500" selected>500</option>
                    <option value="1000">1000</option>
                    <option value="5000">5000</option>
                </select>
            </label>
            <label>
                Level:
                <select id="level-select" onchange="fetchLogs()">
                    <option value="">All</option>
                    <option value="ERROR">ERROR</option>
                    <option value="WARNING">WARNING</option>
                    <option value="INFO">INFO</option>
                    <option value="DEBUG">DEBUG</option>
                </select>
            </label>
            <button onclick="fetchLogs()">Refresh</button>
            <div class="auto-scroll">
                <input type="checkbox" id="auto-scroll" checked>
                <label for="auto-scroll">Auto-scroll</label>
            </div>
            <div class="auto-scroll">
                <input type="checkbox" id="auto-refresh">
                <label for="auto-refresh">Auto-refresh (5s)</label>
            </div>
        </div>
        
        <div id="error-container"></div>
        <div id="logs-container" class="logs-container loading">Loading logs...</div>
    </div>
    
    <script>
        const pid = {pid};
        let autoRefreshInterval = null;
        
        function formatLogEntry(log) {{
            const timestamp = log.timestamp || '';
            const level = (log.level || 'INFO').toUpperCase();
            const message = log.message || '';
            const module = log.module ? `[${{log.module}}]` : '';
            
            return `
                <div class="log-entry">
                    <span class="log-timestamp">${{timestamp}}</span>
                    <span class="log-level ${{level}}">${{level}}</span>
                    ${{module ? `<span style="color: #858585;">${{module}}</span>` : ''}}
                    <span class="log-message">${{escapeHtml(message)}}</span>
                </div>
            `;
        }}
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        async function fetchWorkerInfo() {{
            try {{
                const response = await fetch(`/monitor/worker/${{pid}}`);
                const data = await response.json();
                
                if (data.error) {{
                    document.getElementById('process-info').textContent = 
                        'Error: ' + data.error;
                    return;
                }}
                
                document.getElementById('process-info').innerHTML = 
                    `Process: <strong>${{data.name || 'N/A'}}</strong> | ` +
                    `Status: <strong>${{data.status || 'N/A'}}</strong> | ` +
                    `Uptime: <strong>${{formatUptime(data.uptime_seconds || 0)}}</strong>`;
            }} catch (error) {{
                document.getElementById('process-info').textContent = 
                    'Error loading process info: ' + error.message;
            }}
        }}
        
        function formatUptime(seconds) {{
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = seconds % 60;
            
            if (days > 0) return `${{days}}d ${{hours}}h ${{minutes}}m`;
            if (hours > 0) return `${{hours}}h ${{minutes}}m`;
            if (minutes > 0) return `${{minutes}}m ${{secs}}s`;
            return `${{secs}}s`;
        }}
        
        async function fetchLogs() {{
            try {{
                const limit = document.getElementById('limit-select').value;
                const level = document.getElementById('level-select').value;
                const params = new URLSearchParams({{ limit }});
                if (level) params.append('level', level);
                
                const response = await fetch(`/monitor/worker/${{pid}}/logs?${{params}}`, {{
                    credentials: 'same-origin'
                }});
                
                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                }}
                
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {{
                    throw new Error('Server returned non-JSON response. Authentication may have failed.');
                }}
                
                const data = await response.json();
                
                if (data.error) {{
                    document.getElementById('logs-container').innerHTML = 
                        '<div class="error">Error: ' + data.error + '</div>';
                    document.getElementById('error-container').innerHTML = '';
                    return;
                }}
                
                if (data.logs.length === 0) {{
                    document.getElementById('logs-container').innerHTML = 
                        '<div class="loading">No logs found for this worker</div>';
                    document.getElementById('error-container').innerHTML = '';
                    return;
                }}
                
                let html = '';
                data.logs.forEach(log => {{
                    html += formatLogEntry(log);
                }});
                
                document.getElementById('logs-container').innerHTML = html;
                document.getElementById('error-container').innerHTML = '';
                
                // Auto-scroll to bottom if enabled
                if (document.getElementById('auto-scroll').checked) {{
                    const container = document.getElementById('logs-container');
                    container.scrollTop = container.scrollHeight;
                }}
            }} catch (error) {{
                document.getElementById('logs-container').innerHTML = 
                    '<div class="error">Error fetching logs: ' + error.message + '</div>';
                document.getElementById('error-container').innerHTML = '';
            }}
        }}
        
        function toggleAutoRefresh() {{
            const checkbox = document.getElementById('auto-refresh');
            if (checkbox.checked) {{
                autoRefreshInterval = setInterval(fetchLogs, 5000);
            }} else {{
                if (autoRefreshInterval) {{
                    clearInterval(autoRefreshInterval);
                    autoRefreshInterval = null;
                }}
            }}
        }}
        
        document.getElementById('auto-refresh').addEventListener('change', toggleAutoRefresh);
        
        async function fetchSystemMetrics() {{
            try {{
                const response = await fetch('/monitor/stats');
                const data = await response.json();
                
                if (data.system) {{
                    const cpuPercent = data.system.cpu_percent;
                    const memPercent = data.system.memory_percent;
                    
                    document.getElementById('cpu-percent').textContent = cpuPercent.toFixed(1) + '%';
                    const cpuProgress = document.getElementById('cpu-progress');
                    cpuProgress.style.width = cpuPercent + '%';
                    cpuProgress.className = 'progress-fill' + 
                        (cpuPercent > 80 ? ' danger' : cpuPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-percent').textContent = memPercent.toFixed(1) + '%';
                    const memProgress = document.getElementById('memory-progress');
                    memProgress.style.width = memPercent + '%';
                    memProgress.className = 'progress-fill' + 
                        (memPercent > 80 ? ' danger' : memPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-details').textContent = 
                        data.system.memory_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.memory_total_gb.toFixed(2) + ' GB';
                    
                    const diskPercent = data.system.disk_percent;
                    document.getElementById('disk-percent').textContent = diskPercent.toFixed(1) + '%';
                    const diskProgress = document.getElementById('disk-progress');
                    diskProgress.style.width = diskPercent + '%';
                    diskProgress.className = 'progress-fill' + 
                        (diskPercent > 80 ? ' danger' : diskPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('disk-details').textContent = 
                        data.system.disk_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.disk_total_gb.toFixed(2) + ' GB';
                }}
            }} catch (error) {{
                // Silently fail - don't break the page if system metrics fail
            }}
        }}
        
        // Initial load
        fetchSystemMetrics();
        fetchWorkerInfo();
        fetchLogs();
        
        // Auto-refresh system metrics every 0.5 seconds (matching dashboard)
        setInterval(() => {{
            fetchSystemMetrics();
        }}, 500);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

