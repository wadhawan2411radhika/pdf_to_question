"""Simple PDF Processing Orchestrator."""

import os
from typing import Dict, Any
import pdfplumber
from config import Config
from text_extractor import TextExtractor
from table_extractor import TableExtractor
from simple_enhanced_extractor import SimpleEnhancedExtractor
from state_manager import StateManager
import time

class Orchestrator:
    """Simple orchestrator for PDF processing workflow."""
    
    def __init__(self):
        """Initialize orchestrator."""
        self.config = Config()
    
    def check_density(self, num_pages: int, tables_all_pages: list) -> str:
        """Check if PDF is table dominant or free text dominant."""
        table_pages = sum(1 for tables in tables_all_pages if tables and len(tables) > 0)
        if num_pages == 0:
            return "unknown (no pages)"
        
        ratio = table_pages / num_pages
        if ratio > 0.5:
            return "table-dominant"
        else:
            return "free-text-dominant"
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Process a PDF file and return results."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Analyze PDF density to determine processing strategy
        with pdfplumber.open(pdf_path) as doc:
            tables_all_pages = [page.extract_tables() for page in doc.pages]
            num_pages = len(doc.pages)
            dominance = self.check_density(num_pages, tables_all_pages)
        
        print(f"ORCHESTRATOR - PDF dominance: {dominance}")
        
        # Process based on dominance type
        if dominance == "table-dominant":
            # Use SimpleEnhancedExtractor for table-dominant PDFs
            extractor = SimpleEnhancedExtractor(pdf_path)
            extraction_results = extractor.extract_questions()
            
            # Return clean paths for PDFResponse
            return {
                "status": "success",
                "output_json_path": extraction_results['output_paths']['merged_state'],
                "assets_dir": str(extractor.output_manager.images_dir)
            }
            
        else:
            # Use TextExtractor for text-focused PDFs
            extractor = TextExtractor(pdf_path)
            questions = extractor.extract()
            
            # Return clean paths for PDFResponse
            return {
                "status": "success",
                "output_json_path": extractor.output_paths['merged_state'],
                "assets_dir": str(extractor.output_manager.images_dir)
            }
