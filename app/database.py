"""Database connection and query utilities."""
import pymysql
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager."""
    
    def __init__(self):
        self.connection = None
        self._init_connection()
    
    def _init_connection(self):
        """Initialize database connection."""
        try:
            self.connection = pymysql.connect(
                host=settings.db_host,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name,
                port=settings.db_port,
                charset=settings.db_charset,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    @contextmanager
    def get_cursor(self):
        """Get database cursor with automatic cleanup."""
        try:
            cursor = self.connection.cursor()
            yield cursor
        finally:
            cursor.close()
    
    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Any]:
        """Fetch a single value (equivalent to PHP FetchOne)."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                if result:
                    # If result is a dict, return first value
                    if isinstance(result, dict):
                        return list(result.values())[0] if result else None
                    return result
                return None
        except Exception as e:
            logger.error(f"Query error: {e}\nQuery: {query}")
            raise
    
    def fetch_row(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Fetch a single row (equivalent to PHP FetchRow)."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Query error: {e}\nQuery: {query}")
            raise
    
    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows (equivalent to PHP FetchAll)."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query error: {e}\nQuery: {query}")
            raise
    
    def execute(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute a query and return affected rows."""
        try:
            with self.get_cursor() as cursor:
                affected = cursor.execute(query, params)
                self.connection.commit()
                return affected
        except Exception as e:
            logger.error(f"Query error: {e}\nQuery: {query}")
            self.connection.rollback()
            raise
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")


# Global database instance
db = Database()

