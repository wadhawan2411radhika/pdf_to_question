"""
Image-to-Table-Cell Mapping Module

This module provides functionality to map images within PDF table cells to their 
corresponding table cells using coordinate-based spatial analysis.
"""

import fitz  # PyMuPDF
import pdfplumber
import json
import os
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ImageInfo:
    """Information about an extracted image"""
    page_number: int
    image_index: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    file_path: str
    xref: int
    width: int
    height: int

@dataclass
class TableCell:
    """Information about a table cell"""
    page_number: int
    table_index: int
    row_index: int
    col_index: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    text: str
    
@dataclass
class TableInfo:
    """Information about a table"""
    page_number: int
    table_index: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    cells: List[TableCell]

@dataclass
class ImageCellMapping:
    """Mapping between an image and a table cell"""
    image: ImageInfo
    cell: TableCell
    confidence_score: float  # 0-1, based on overlap and proximity
    overlap_area: float
    
class ImageTableMapper:
    """
    Maps images to table cells using coordinate-based spatial analysis
    """
    
    def __init__(self, pdf_path: str, output_dir: str = "output"):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.doc = None
        self.pdf_plumber = None
        
        # Create output directories
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "cell_image_snips"), exist_ok=True)
        
        logger.info(f"ImageTableMapper initialized for {pdf_path}")
    
    def __enter__(self):
        """Context manager entry"""
        self.doc = fitz.open(self.pdf_path)
        self.pdf_plumber = pdfplumber.open(self.pdf_path)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.doc:
            self.doc.close()
        if self.pdf_plumber:
            self.pdf_plumber.close()
    
    def extract_images_with_coordinates(self) -> List[ImageInfo]:
        """
        Extract images from PDF with their coordinate information
        """
        images = []
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            
            # Get image list with coordinates
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                try:
                    # Extract image data
                    xref = img[0]
                    base_image = self.doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Get image coordinates on the page
                    image_rects = page.get_image_rects(xref)
                    
                    if image_rects:
                        # Use the first rectangle if multiple exist
                        rect = image_rects[0]
                        bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
                    else:
                        # Fallback: try to find image by searching page content
                        bbox = self._find_image_bbox_fallback(page, xref)
                    
                    # Save image file
                    image_filename = f"page{page_num+1}_img{img_index+1}.{image_ext}"
                    image_path = os.path.join(self.output_dir, "images", image_filename)
                    
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    
                    # Create ImageInfo object
                    image_info = ImageInfo(
                        page_number=page_num + 1,
                        image_index=img_index + 1,
                        bbox=bbox,
                        file_path=image_path,
                        xref=xref,
                        width=base_image["width"],
                        height=base_image["height"]
                    )
                    
                    images.append(image_info)
                    logger.info(f"Extracted image: {image_filename} at {bbox}")
                    
                except Exception as e:
                    logger.error(f"Error extracting image {img_index} from page {page_num}: {e}")
        
        logger.info(f"Total images extracted: {len(images)}")
        return images
    
    def _find_image_bbox_fallback(self, page, xref) -> Tuple[float, float, float, float]:
        """
        Fallback method to find image bounding box by searching page content
        """
        try:
            # Search through page content for image references
            content = page.get_text("dict")
            
            # Look for image in blocks
            for block in content.get("blocks", []):
                if "image" in block:
                    if block.get("xref") == xref:
                        bbox = block.get("bbox", (0, 0, 100, 100))
                        return bbox
            
            # If not found, return default bbox
            return (0, 0, 100, 100)
            
        except Exception as e:
            logger.warning(f"Fallback bbox search failed: {e}")
            return (0, 0, 100, 100)
    
    def extract_tables_with_coordinates(self) -> List[TableInfo]:
        """
        Extract tables with cell coordinate information using pdfplumber
        """
        tables = []
        
        for page_num, page in enumerate(self.pdf_plumber.pages):
            # Extract tables with bbox information
            page_tables = page.find_tables()
            
            for table_index, table in enumerate(page_tables):
                try:
                    # Get table bbox
                    table_bbox = table.bbox
                    
                    # Extract table data
                    table_data = table.extract()
                    if not table_data:
                        continue
                    
                    # Get cell coordinates
                    cells = []
                    for row_index, row in enumerate(table_data):
                        for col_index, cell_text in enumerate(row):
                            # Calculate cell bbox based on table structure
                            cell_bbox = self._calculate_cell_bbox(
                                table, table_bbox, row_index, col_index, len(table_data), len(row)
                            )
                            
                            cell = TableCell(
                                page_number=page_num + 1,
                                table_index=table_index + 1,
                                row_index=row_index,
                                col_index=col_index,
                                bbox=cell_bbox,
                                text=str(cell_text).strip() if cell_text else ""
                            )
                            cells.append(cell)
                    
                    table_info = TableInfo(
                        page_number=page_num + 1,
                        table_index=table_index + 1,
                        bbox=table_bbox,
                        cells=cells
                    )
                    
                    tables.append(table_info)
                    logger.info(f"Extracted table {table_index+1} from page {page_num+1} with {len(cells)} cells")
                    
                except Exception as e:
                    logger.error(f"Error extracting table {table_index} from page {page_num}: {e}")
        
        logger.info(f"Total tables extracted: {len(tables)}")
        return tables
    
    def _calculate_cell_bbox(self, table, table_bbox: Tuple[float, float, float, float], 
                           row_index: int, col_index: int, total_rows: int, total_cols: int) -> Tuple[float, float, float, float]:
        """
        Calculate individual cell bounding box based on table structure
        """
        x0, y0, x1, y1 = table_bbox
        
        # Calculate cell dimensions
        cell_width = (x1 - x0) / total_cols
        cell_height = (y1 - y0) / total_rows
        
        # Calculate cell coordinates
        cell_x0 = x0 + (col_index * cell_width)
        cell_y0 = y0 + (row_index * cell_height)
        cell_x1 = cell_x0 + cell_width
        cell_y1 = cell_y0 + cell_height
        
        return (cell_x0, cell_y0, cell_x1, cell_y1)
    
    def map_images_to_cells(self, images: List[ImageInfo], tables: List[TableInfo], 
                           overlap_threshold: float = 0.1) -> List[ImageCellMapping]:
        """
        Map images to table cells based on coordinate overlap and proximity
        
        Args:
            images: List of extracted images with coordinates
            tables: List of extracted tables with cell coordinates
            overlap_threshold: Minimum overlap ratio to consider a match
            
        Returns:
            List of image-cell mappings with confidence scores
        """
        mappings = []
        
        for image in images:
            best_matches = []
            
            # Find tables on the same page
            page_tables = [t for t in tables if t.page_number == image.page_number]
            
            for table in page_tables:
                for cell in table.cells:
                    # Calculate overlap and proximity
                    overlap_area = self._calculate_overlap_area(image.bbox, cell.bbox)
                    proximity_score = self._calculate_proximity_score(image.bbox, cell.bbox)
                    
                    # Calculate confidence score
                    image_area = self._calculate_area(image.bbox)
                    cell_area = self._calculate_area(cell.bbox)
                    
                    if image_area > 0:
                        overlap_ratio = overlap_area / image_area
                    else:
                        overlap_ratio = 0
                    
                    # Combined confidence score (overlap + proximity)
                    confidence_score = (overlap_ratio * 0.7) + (proximity_score * 0.3)
                    
                    # Only consider matches above threshold
                    if overlap_ratio >= overlap_threshold or confidence_score >= 0.3:
                        mapping = ImageCellMapping(
                            image=image,
                            cell=cell,
                            confidence_score=confidence_score,
                            overlap_area=overlap_area
                        )
                        best_matches.append(mapping)
            
            # Sort by confidence and take the best match
            if best_matches:
                best_matches.sort(key=lambda x: x.confidence_score, reverse=True)
                mappings.append(best_matches[0])
                
                logger.info(f"Mapped image {image.file_path} to cell ({best_matches[0].cell.row_index}, "
                           f"{best_matches[0].cell.col_index}) with confidence {best_matches[0].confidence_score:.3f}")
        
        logger.info(f"Total mappings created: {len(mappings)}")
        return mappings
    
    def _calculate_overlap_area(self, bbox1: Tuple[float, float, float, float], 
                               bbox2: Tuple[float, float, float, float]) -> float:
        """Calculate the overlap area between two bounding boxes"""
        x0_1, y0_1, x1_1, y1_1 = bbox1
        x0_2, y0_2, x1_2, y1_2 = bbox2
        
        # Calculate intersection
        x0_int = max(x0_1, x0_2)
        y0_int = max(y0_1, y0_2)
        x1_int = min(x1_1, x1_2)
        y1_int = min(y1_1, y1_2)
        
        # Check if there's an intersection
        if x0_int < x1_int and y0_int < y1_int:
            return (x1_int - x0_int) * (y1_int - y0_int)
        else:
            return 0.0
    
    def _calculate_proximity_score(self, bbox1: Tuple[float, float, float, float], 
                                  bbox2: Tuple[float, float, float, float]) -> float:
        """Calculate proximity score (1.0 = same position, 0.0 = far apart)"""
        # Calculate centers
        center1_x = (bbox1[0] + bbox1[2]) / 2
        center1_y = (bbox1[1] + bbox1[3]) / 2
        center2_x = (bbox2[0] + bbox2[2]) / 2
        center2_y = (bbox2[1] + bbox2[3]) / 2
        
        # Calculate distance
        distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5
        
        # Normalize distance (assuming page width ~600 points)
        max_distance = 600
        proximity_score = max(0, 1 - (distance / max_distance))
        
        return proximity_score
    
    def _calculate_area(self, bbox: Tuple[float, float, float, float]) -> float:
        """Calculate area of a bounding box"""
        return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    
    def extract_cell_image_snippets(self, mappings: List[ImageCellMapping]) -> Dict[str, Any]:
        """
        Extract image snippets for each mapped cell and save them
        
        Returns:
            Dictionary with mapping information and snippet paths
        """
        snippet_info = {
            "mappings": [],
            "total_mappings": len(mappings),
            "snippet_directory": os.path.join(self.output_dir, "cell_image_snips")
        }
        
        for i, mapping in enumerate(mappings):
            try:
                # Create snippet filename
                snippet_filename = f"cell_p{mapping.cell.page_number}_t{mapping.cell.table_index}_r{mapping.cell.row_index}_c{mapping.cell.col_index}.png"
                snippet_path = os.path.join(self.output_dir, "cell_image_snips", snippet_filename)
                
                # Extract cell region from page as image
                page = self.doc[mapping.cell.page_number - 1]
                
                # Create pixmap for the cell region
                cell_rect = fitz.Rect(mapping.cell.bbox)
                mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat, clip=cell_rect)
                
                # Save snippet
                pix.save(snippet_path)
                pix = None  # Free memory
                
                # Add to mapping info
                mapping_info = {
                    "image_path": mapping.image.file_path,
                    "cell_position": {
                        "page": mapping.cell.page_number,
                        "table": mapping.cell.table_index,
                        "row": mapping.cell.row_index,
                        "column": mapping.cell.col_index
                    },
                    "cell_text": mapping.cell.text,
                    "confidence_score": mapping.confidence_score,
                    "overlap_area": mapping.overlap_area,
                    "cell_bbox": mapping.cell.bbox,
                    "image_bbox": mapping.image.bbox,
                    "snippet_path": snippet_path
                }
                
                snippet_info["mappings"].append(mapping_info)
                logger.info(f"Created cell snippet: {snippet_filename}")
                
            except Exception as e:
                logger.error(f"Error creating snippet for mapping {i}: {e}")
        
        return snippet_info
    
    def generate_mapping_report(self, mappings: List[ImageCellMapping]) -> Dict[str, Any]:
        """
        Generate a comprehensive report of image-to-cell mappings
        """
        report = {
            "pdf_path": self.pdf_path,
            "total_mappings": len(mappings),
            "mapping_summary": {},
            "detailed_mappings": [],
            "statistics": {
                "avg_confidence": 0,
                "high_confidence_count": 0,
                "medium_confidence_count": 0,
                "low_confidence_count": 0
            }
        }
        
        # Calculate statistics
        if mappings:
            confidences = [m.confidence_score for m in mappings]
            report["statistics"]["avg_confidence"] = sum(confidences) / len(confidences)
            
            for conf in confidences:
                if conf >= 0.7:
                    report["statistics"]["high_confidence_count"] += 1
                elif conf >= 0.4:
                    report["statistics"]["medium_confidence_count"] += 1
                else:
                    report["statistics"]["low_confidence_count"] += 1
        
        # Group by page
        page_summary = {}
        for mapping in mappings:
            page_num = mapping.cell.page_number
            if page_num not in page_summary:
                page_summary[page_num] = []
            
            page_summary[page_num].append({
                "table": mapping.cell.table_index,
                "cell": f"({mapping.cell.row_index}, {mapping.cell.col_index})",
                "confidence": mapping.confidence_score,
                "image_file": os.path.basename(mapping.image.file_path)
            })
        
        report["mapping_summary"] = page_summary
        
        # Detailed mappings
        for mapping in mappings:
            detail = {
                "image": asdict(mapping.image),
                "cell": asdict(mapping.cell),
                "confidence_score": mapping.confidence_score,
                "overlap_area": mapping.overlap_area
            }
            report["detailed_mappings"].append(detail)
        
        return report
    
    def process_pdf(self, overlap_threshold: float = 0.1) -> Dict[str, Any]:
        """
        Complete pipeline to process PDF and create image-to-cell mappings
        
        Args:
            overlap_threshold: Minimum overlap ratio for mapping
            
        Returns:
            Dictionary containing all results and file paths
        """
        logger.info(f"Starting complete PDF processing pipeline for {self.pdf_path}")
        
        try:
            # Extract images with coordinates
            images = self.extract_images_with_coordinates()
            
            # Extract tables with cell coordinates
            tables = self.extract_tables_with_coordinates()
            
            # Create mappings
            mappings = self.map_images_to_cells(images, tables, overlap_threshold)
            
            # Extract cell snippets
            snippet_info = self.extract_cell_image_snippets(mappings)
            
            # Generate report
            report = self.generate_mapping_report(mappings)
            
            # Save results
            results = {
                "images": [asdict(img) for img in images],
                "tables": [asdict(table) for table in tables],
                "mappings": [asdict(mapping) for mapping in mappings],
                "snippet_info": snippet_info,
                "report": report
            }
            
            # Save to JSON file
            output_json_path = os.path.join(self.output_dir, "image_table_mappings.json")
            with open(output_json_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Processing complete. Results saved to {output_json_path}")
            
            return {
                "status": "success",
                "output_json_path": output_json_path,
                "images_dir": os.path.join(self.output_dir, "images"),
                "snippets_dir": os.path.join(self.output_dir, "cell_image_snips"),
                "total_images": len(images),
                "total_tables": len(tables),
                "total_mappings": len(mappings)
            }
            
        except Exception as e:
            logger.error(f"Error in PDF processing pipeline: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
