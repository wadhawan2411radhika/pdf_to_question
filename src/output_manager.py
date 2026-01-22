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
        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent
        self.base_output_dir = project_root / base_output_dir
        
        if pdf_name:
            # Create PDF-specific directory structure: output/<pdf_name>/
            self.pdf_name_clean = Path(pdf_name).stem  # Remove .pdf extension
            self.pdf_output_dir = self.base_output_dir / self.pdf_name_clean
            self.json_dir = self.pdf_output_dir
            self.images_dir = self.pdf_output_dir / "assets"
        else:
            # Fallback to old structure
            self.pdf_output_dir = self.base_output_dir
            self.json_dir = self.base_output_dir / "json"
            self.images_dir = self.base_output_dir / "images"
        
        # Create directories (no separate log directories for PDFs)
        self.json_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
    
    def save_images(self, workflow_state, pdf_name: str) -> List[str]:
        """Save extracted images to organized directory structure."""
        saved_images = []
        
        # Create PDF-specific image directory
        pdf_images_dir = self.images_dir / pdf_name.replace(".pdf", "")
        pdf_images_dir.mkdir(exist_ok=True)
        
        try:
            for page_content in workflow_state.sampled_pages:
                page_num = page_content["page_number"]
                
                # Save page screenshot
                if page_content.get("page_image"):
                    page_img_path = pdf_images_dir / f"page_{page_num}.png"
                    with open(page_img_path, "wb") as f:
                        f.write(page_content["page_image"])
                    saved_images.append(f"page_{page_num}.png")
                    logger.info(f"Saved page image: {page_img_path}")
                
                # Save extracted images
                for img in page_content.get("images", []):
                    img_filename = f"page_{page_num}_img_{img['index']}.png"
                    img_path = pdf_images_dir / img_filename
                    with open(img_path, "wb") as f:
                        f.write(img["data"])
                    saved_images.append(img_filename)
                    logger.info(f"Saved extracted image: {img_path}")
        
        except Exception as e:
            logger.error(f"Error saving images: {e}")
        
        return saved_images
