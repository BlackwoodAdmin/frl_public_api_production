"""Authentication service."""
from app.database import db
from typing import Optional
import logging
import os
import traceback

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
    logger.debug(f"validate_dashboard_credentials: Validation called for username: {username}, password: **** (masked)")
    
    try:
        expected_username = os.getenv("DASHBOARD_USERNAME", "")
        expected_password = os.getenv("DASHBOARD_PASSWORD", "")
        
        logger.debug(f"validate_dashboard_credentials: DASHBOARD_USERNAME env var present: {bool(expected_username)}")
        logger.debug(f"validate_dashboard_credentials: DASHBOARD_PASSWORD env var present: {bool(expected_password)}")
        
        if not expected_username or not expected_password:
            logger.warning("validate_dashboard_credentials: Dashboard credentials not configured in environment")
            if not expected_username:
                logger.warning("validate_dashboard_credentials: DASHBOARD_USERNAME environment variable is missing or empty")
            if not expected_password:
                logger.warning("validate_dashboard_credentials: DASHBOARD_PASSWORD environment variable is missing or empty")
            return False
        
        username_match = username == expected_username
        password_match = password == expected_password
        
        logger.debug(f"validate_dashboard_credentials: Username match: {username_match}")
        logger.debug(f"validate_dashboard_credentials: Password match: {password_match}")
        
        validation_result = username_match and password_match
        logger.debug(f"validate_dashboard_credentials: Validation result: {validation_result}")
        
        return validation_result
    except Exception as e:
        logger.error(f"validate_dashboard_credentials: Error validating dashboard credentials: {e}")
        logger.error(f"validate_dashboard_credentials: Exception traceback: {traceback.format_exc()}")
        return False

