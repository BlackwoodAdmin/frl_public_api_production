"""Logging utilities for POST variable logging."""
import logging
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def log_post_variables(
    endpoint: str,
    method: str,
    url: str,
    query_params: Optional[Dict[str, Any]] = None,
    form_data: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    raw_body: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None
):
    """
    Log POST variables and request details to a file in the app root directory.
    
    Args:
        endpoint: Endpoint name (e.g., "Article.php" or "Articles.php")
        method: HTTP method (GET or POST)
        url: Full request URL
        query_params: Query parameters as dict
        form_data: Form data as dict (if present)
        json_data: JSON data as dict (if present)
        raw_body: Raw body as string (if form_data and json_data are both None)
        headers: Request headers as dict
    """
    try:
        # Get app root directory (parent of app/)
        # __file__ is app/utils/logging.py
        # .parent = app/utils/
        # .parent.parent = app/
        # .parent.parent.parent = root/
        app_root = Path(__file__).parent.parent.parent
        
        # Determine log file name based on endpoint
        if endpoint == "Article.php":
            log_file = app_root / "article_post_vars.log"
        elif endpoint == "Articles.php":
            log_file = app_root / "articles_post_vars.log"
        else:
            # Fallback to generic name
            log_file = app_root / f"{endpoint.lower().replace('.php', '')}_post_vars.log"
        
        # Prepare log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "method": method,
            "url": url,
            "query_params": dict(query_params) if query_params else {},
            "post_variables": {
                "form_data": dict(form_data) if form_data else None,
                "json_data": json_data if json_data else None,
                "raw_body": raw_body if raw_body else None
            },
            "headers": dict(headers) if headers else {}
        }
        
        # Convert form_data values to strings if they're not already
        # (FastAPI Form objects might be special types)
        if log_entry["post_variables"]["form_data"]:
            cleaned_form_data = {}
            for key, value in log_entry["post_variables"]["form_data"].items():
                try:
                    # Try to convert to string if it's not already
                    if hasattr(value, '__str__'):
                        cleaned_form_data[str(key)] = str(value)
                    else:
                        cleaned_form_data[str(key)] = value
                except Exception:
                    cleaned_form_data[str(key)] = repr(value)
            log_entry["post_variables"]["form_data"] = cleaned_form_data
        
        # Write to file (creates file if it doesn't exist)
        # Use 'a' mode (append) - file will be created if it doesn't exist
        with open(str(log_file), "a", encoding="utf-8") as f:
            json_str = json.dumps(log_entry) + "\n"
            bytes_written = f.write(json_str)
            f.flush()  # Ensure data is written immediately
            os.fsync(f.fileno())  # Force write to disk
        
        # Log success to standard logger for verification (optional, can be removed if too verbose)
        # logger.debug(f"POST vars log written: {bytes_written} bytes to {log_file}")
    except PermissionError as e:
        # Log permission errors to standard logger
        logger.error(f"Permission denied writing POST vars log to {log_file}: {e}")
    except Exception as e:
        # Log other errors to standard logger as fallback
        logger.error(f"Failed to write POST vars log: {e}")
        import traceback
        logger.error(traceback.format_exc())

