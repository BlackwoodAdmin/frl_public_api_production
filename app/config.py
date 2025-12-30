"""Configuration management for the application."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database settings
    db_host: str = "10.248.48.202"
    db_name: str = "freerele_blackwoodproductions"
    db_user: str = "freerele_bwp"
    db_password: str = ""
    db_port: int = 3306
    db_charset: str = "utf8mb4"
    
    # Application settings
    debug: bool = False
    log_level: str = "INFO"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

