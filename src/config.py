"""Configuration module for PDF Ingestion AI Agent."""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration settings for the PDF Ingestion AI Agent."""
    
    # LLM Configuration
    LITELLM_API_URL: str = os.getenv("LITELLM_API_URL")
    LITELLM_API_KEY: str = os.getenv("LITELLM_API_KEY")
    LITELLM_MODEL: str = os.getenv("LITELLM_MODEL")

    # PDF Processing Configuration
    MAX_PARALLEL_PDFS: int = os.getenv("MAX_PARALLEL_PDFS", 5)

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings."""
        if not cls.LITELLM_API_KEY:
            raise ValueError("LITELLM_API_KEY is required")
        return True

def setup_logging() -> logging.Logger:
    """Set up logging configuration."""
    # Use absolute path for log file so it's always in the project root
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_file_path = os.path.join(project_root, "extraction_debug.log")
    
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper()),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file_path, mode='a')
        ],
        force=True  # Force reconfiguration to override any existing setup
    )
    return logging.getLogger(__name__)
