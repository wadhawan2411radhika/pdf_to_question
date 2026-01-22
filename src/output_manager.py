"""
Output Management Module
Handles saving of extraction outputs to organized directories.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional


logger = logging.getLogger(__name__)

class OutputManager:
    """Manages saving of extraction outputs to organized directories."""
    
    def __init__(self, base_output_dir: str = "output", pdf_name: str = None):
        # Handle both absolute and relative paths correctly
        base_path = Path(base_output_dir)
        
        if base_path.is_absolute():
            # Use absolute path as-is
            self.base_output_dir = base_path
        else:
            # Make relative path relative to project root
            project_root = Path(__file__).parent.parent
            self.base_output_dir = project_root / base_output_dir
        
        if pdf_name:
            # Create PDF-specific directory structure: output/<pdf_name>/
            self.pdf_name_clean = Path(pdf_name).stem  # Remove .pdf extension
            self.pdf_output_dir = self.base_output_dir / self.pdf_name_clean
            self.images_dir = self.pdf_output_dir / "assets"
            self.json_dir = self.pdf_output_dir  # JSON files go in the main PDF directory
        else:
            # Fallback to old structure
            self.pdf_output_dir = self.base_output_dir
            self.images_dir = self.base_output_dir / "images"
            self.json_dir = self.base_output_dir
        
        # Create directories
        try:
            self.images_dir.mkdir(parents=True, exist_ok=True)
            self.json_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"OutputManager initialized: base_dir={self.base_output_dir}, images_dir={self.images_dir}, json_dir={self.json_dir}")
        except Exception as e:
            logger.error(f"Failed to create output directories: {e}")
            raise
