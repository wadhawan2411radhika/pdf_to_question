"""
Simple Image-to-Table-Cell Mapper

Maps images to table cells based on Y-axis positioning.
Logic: Find the table cell that starts just above the image.
"""

import fitz  # PyMuPDF
import pdfplumber
import json
import os
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class SimpleImageMapper:
    """
    Simple mapper that associates images with table cells based on Y-axis positioning
    """
    
    def __init__(self, pdf_path: str, output_manager=None):
        self.pdf_path = pdf_path
        self.output_manager = output_manager
        logger.info(f"SimpleImageMapper initialized for {pdf_path}")
    
    def map_images_to_cells(self) -> Dict[str, Any]:
        """
        Main function to map images to cells
        
        Returns:
            Dictionary with mappings and extracted files
        """
        logger.info("Starting image-to-cell mapping process")
        
        # Extract images with Y positions
        logger.info("Extracting images with Y positions")
        images = self._extract_images()
        
        # Extract table cells with Y positions
        logger.info("Extracting table cells with Y positions")
        cells = self._extract_table_cells()
        
        # Create mappings based on Y-axis
        logger.info("Creating Y-axis based mappings")
        mappings = self._create_y_axis_mappings(images, cells)
        
        logger.info(f"Image mapping completed: {len(images)} images, {len(cells)} cells, {len(mappings)} mappings")
        return {
            "mappings": mappings,
            "total_images": len(images),
            "total_cells": len(cells),
            "total_mappings": len(mappings)
        }
    
    def _extract_images(self) -> List[Dict]:
        """Extract images with their Y positions"""
        images = []
        
        with fitz.open(self.pdf_path) as doc:
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                for img_index, img in enumerate(page.get_images(full=True)):
                    try:
                        xref = img[0]
                        
                        # Get image position
                        image_rects = page.get_image_rects(xref)
                        if image_rects:
                            rect = image_rects[0]
                            y_start = rect.y0  # Top Y coordinate
                            
                            # Save image
                            base_image = doc.extract_image(xref)
                            image_bytes = base_image["image"]
                            image_ext = base_image["ext"]
                            
                            # Use OutputManager if available, otherwise fallback to simple_output
                            if self.output_manager:
                                image_filename = f"page{page_num+1}_img{img_index+1}.{image_ext}"
                                image_path = self.output_manager.images_dir / image_filename
                            else:
                                os.makedirs("simple_output/images", exist_ok=True)
                                image_filename = f"page{page_num+1}_img{img_index+1}.{image_ext}"
                                image_path = f"simple_output/images/{image_filename}"
                            
                            with open(image_path, "wb") as f:
                                f.write(image_bytes)
                            
                            images.append({
                                "page": page_num + 1,
                                "image_index": img_index + 1,
                                "y_start": y_start,
                                "file_path": str(image_path),
                                "bbox": (rect.x0, rect.y0, rect.x1, rect.y1)
                            })
                            
                    except Exception as e:
                        logger.error(f"Error extracting image {img_index} from page {page_num+1}: {e}")
        
        return images
    
    def _extract_table_cells(self) -> List[Dict]:
        """Extract table cells with their Y positions"""
        cells = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.find_tables()
                
                for table_index, table in enumerate(tables):
                    try:
                        table_data = table.extract()
                        if not table_data:
                            continue
                        
                        # Get table bbox
                        table_bbox = table.bbox
                        x0, y0, x1, y1 = table_bbox
                        
                        # Calculate cell positions
                        num_rows = len(table_data)
                        num_cols = len(table_data[0]) if num_rows > 0 else 0
                        
                        if num_rows == 0 or num_cols == 0:
                            continue
                        
                        cell_height = (y1 - y0) / num_rows
                        
                        for row_index, row in enumerate(table_data):
                            for col_index, cell_text in enumerate(row):
                                # Calculate cell Y position
                                cell_y_start = y0 + (row_index * cell_height)
                                cell_y_end = cell_y_start + cell_height
                                
                                cells.append({
                                    "page": page_num + 1,
                                    "table_index": table_index + 1,
                                    "row": row_index,
                                    "col": col_index,
                                    "y_start": cell_y_start,
                                    "y_end": cell_y_end,
                                    "text": str(cell_text).strip() if cell_text else "",
                                    "bbox": (x0, cell_y_start, x1, cell_y_end)
                                })
                                
                    except Exception as e:
                        logger.error(f"Error extracting table {table_index} from page {page_num+1}: {e}")
        
        return cells
    
    def _create_y_axis_mappings(self, images: List[Dict], cells: List[Dict]) -> List[Dict]:
        """
        Create mappings based on Y-axis positioning
        
        Logic: For each image, find the cell where the image's bottom Y coordinate falls within
        """
        mappings = []
        
        for image in images:
            image_y_bottom = image["bbox"][3]  # Bottom Y coordinate (y1)
            image_page = image["page"]
            
            # Find cells on the same page
            page_cells = [cell for cell in cells if cell["page"] == image_page]
            
            # Find the cell where image's bottom Y falls within the cell's Y range
            best_cell = None
            
            for cell in page_cells:
                cell_y_start = cell["y_start"]
                cell_y_end = cell["y_end"]
                
                # Check if image's bottom Y coordinate falls within this cell's Y range
                if cell_y_start <= image_y_bottom <= cell_y_end:
                    best_cell = cell
                    break  # Found exact match, no need to continue
            
            if best_cell:
                mappings.append({
                    "image": image,
                    "cell": best_cell,
                    "image_bottom_y": image_y_bottom,
                    "cell_y_range": f"{best_cell['y_start']:.1f} - {best_cell['y_end']:.1f}",
                    "mapping_logic": f"Image bottom Y={image_y_bottom:.1f} falls within cell Y range [{best_cell['y_start']:.1f}, {best_cell['y_end']:.1f}]"
                })
                
                logger.info(f"Mapped {os.path.basename(image['file_path'])} to cell ({best_cell['row']}, {best_cell['col']}) - Image bottom Y: {image_y_bottom:.1f} in cell range [{best_cell['y_start']:.1f}, {best_cell['y_end']:.1f}]")
            else:
                logger.warning(f"No cell found for image {os.path.basename(image['file_path'])} with bottom Y: {image_y_bottom:.1f}")
        
        return mappings
