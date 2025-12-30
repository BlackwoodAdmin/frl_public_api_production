"""Authentication service."""
from app.database import db
from typing import Optional
import logging

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

