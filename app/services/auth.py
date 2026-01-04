"""Authentication service."""
from app.database import db
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)


def validate_api_credentials(apiid: str, apikey: str) -> Optional[int]:
    """
    Validate API credentials against bwp_register table.
    Returns userid if valid, None otherwise.
    """
    try:
        sql = "SELECT id FROM bwp_register WHERE id = %s AND apikey = %s AND deleted != 1"
        userid = db.fetch_one(sql, (apiid, apikey))
        return userid
    except Exception as e:
        logger.error(f"Error validating API credentials: {e}")
        return None


def validate_dashboard_credentials(username: str, password: str) -> bool:
    """Validate dashboard login credentials."""
    try:
        expected_username = os.getenv("DASHBOARD_USERNAME", "")
        expected_password = os.getenv("DASHBOARD_PASSWORD", "")
        
        if not expected_username or not expected_password:
            logger.warning("Dashboard credentials not configured in environment")
            return False
        
        return username == expected_username and password == expected_password
    except Exception as e:
        logger.error(f"Error validating dashboard credentials: {e}")
        return False

