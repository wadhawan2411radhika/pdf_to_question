"""Simple PDF Processing Orchestrator."""

import os
import logging
from typing import Dict, Any
import pdfplumber
from config import Config
from text_pipeline.text_extractor import TextExtractor
from src.table_pipeline.table_vision_extractor import TableVisionExtractor

logger = logging.getLogger(__name__)

class Orchestrator:
    """Simple orchestrator for PDF processing workflow."""
    
    def __init__(self):
        """Initialize orchestrator."""
        self.config = Config()
        logger.info("Orchestrator initialized")
    
    def check_density(self, num_pages: int, tables_all_pages: list) -> str:
        """Check if PDF is table dominant or free text dominant."""
        table_pages = sum(1 for tables in tables_all_pages if tables and len(tables) > 0)
        if num_pages == 0:
            logger.warning("PDF has no pages")
            return "unknown (no pages)"
        
        ratio = table_pages / num_pages
        logger.info(f"PDF analysis: {table_pages}/{num_pages} pages have tables (ratio: {ratio:.2f})")
        
        if ratio > 0.5:
            logger.info("PDF classified as table-dominant")
            return "table-dominant"
        else:
            logger.info("PDF classified as free-text-dominant")
            return "free-text-dominant"
    
    def process_pdf(self, pdf_path: str, output_dir: str = "output") -> Dict[str, Any]:
        """Process a PDF file and return results."""
        logger.info(f"Starting PDF processing: {pdf_path}")
        logger.info(f"Output directory: {output_dir}")
        
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Analyze PDF density to determine processing strategy
        logger.info("Analyzing PDF structure to determine processing strategy")
        with pdfplumber.open(pdf_path) as doc:
            tables_all_pages = [page.extract_tables() for page in doc.pages]
            num_pages = len(doc.pages)
            dominance = self.check_density(num_pages, tables_all_pages)
        
        logger.info(f"PDF dominance determined: {dominance}")
        
        # Process based on dominance type
        if dominance == "table-dominant":
            logger.info("Using TableVisionExtractor for table-dominant PDF")
            extractor = TableVisionExtractor(pdf_path, output_dir=output_dir)
            extraction_results = extractor.extract_questions()
            
            logger.info(f"Table-dominant processing completed. Output: {extraction_results['output_paths']['merged_state']}")
            return {
                "status": "success",
                "output_json_path": extraction_results['output_paths']['merged_state'],
                "assets_dir": str(extractor.output_manager.images_dir)
            }
            
        else:
            logger.info("Using TextExtractor for text-focused PDF")
            extractor = TextExtractor(pdf_path, output_dir=output_dir)
            questions = extractor.extract()
            
            logger.info(f"Text-focused processing completed. Output: {extractor.output_paths['merged_state']}")
            return {
                "status": "success",
                "output_json_path": extractor.output_paths['merged_state'],
                "assets_dir": str(extractor.output_manager.images_dir)
            }
