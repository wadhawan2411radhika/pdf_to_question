"""
Coordinate-based table extractor and mapper
"""
import fitz
import pdfplumber
import re
import json
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class CoordinateTableMapper:
    def __init__(self, pdf_path: str, output_manager=None):
        self.pdf_path = pdf_path
        self.output_manager = output_manager
    
    def extract_and_link_tables(self) -> List[Dict]:
        """Extract tables and link them to questions using coordinates"""
        # Extract tables with coordinates
        tables = self._extract_tables()
        if not tables:
            return []
        
        # Extract questions with coordinates  
        questions = self._extract_questions()
        
        # Link tables to questions
        return self._link_tables_to_questions(tables, questions)
    
    def _extract_tables(self) -> List[Dict]:
        """Extract tables with coordinates and save to files"""
        tables = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                for table_index, table in enumerate(page.find_tables()):
                    table_data = table.extract()
                    if not table_data:
                        continue
                    
                    # Clean table data
                    cleaned_table = [[cell.strip() if cell else "" for cell in row] for row in table_data]
                    
                    # Save table file
                    filename = f"page{page_num+1}_table{table_index+1}.json"
                    if self.output_manager:
                        filepath = self.output_manager.images_dir / filename
                    else:
                        os.makedirs("output/assets", exist_ok=True)
                        filepath = f"output/assets/{filename}"
                    
                    with open(filepath, 'w') as f:
                        json.dump({
                            'table_data': cleaned_table,
                            'rows': len(cleaned_table),
                            'columns': len(cleaned_table[0]) if cleaned_table else 0,
                            'page_number': page_num + 1,
                            'table_index': table_index + 1
                        }, f, indent=2)
                    
                    # Store table info with coordinates
                    x0, y0, x1, y1 = table.bbox
                    tables.append({
                        'path': str(filepath),
                        'filename': filename,
                        'page_number': page_num + 1,
                        'y_coordinate': y0,
                        'bbox': {'x': x0, 'y': y0, 'width': x1-x0, 'height': y1-y0},
                        'rows': len(cleaned_table),
                        'columns': len(cleaned_table[0]) if cleaned_table else 0
                    })
        
        logger.info(f"Extracted {len(tables)} tables")
        return tables
    
    def _extract_questions(self) -> List[Dict]:
        """Extract questions with their Y coordinates"""
        questions = []
        doc = fitz.open(self.pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_dict = page.get_text("dict")
            
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    line_text = ""
                    line_bbox = None
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                        if line_bbox is None:
                            line_bbox = span.get("bbox")
                    
                    line_text = line_text.strip()
                    if re.match(r'^(Question\s+\d+|\d+\.)', line_text, re.IGNORECASE):
                        questions.append({
                            'page': page_num + 1,
                            'question_number': line_text,
                            'y_coordinate': line_bbox[1] if line_bbox else 0
                        })
        
        doc.close()
        return questions
    
    def _link_tables_to_questions(self, tables: List[Dict], questions: List[Dict]) -> List[Dict]:
        """Link tables to questions based on Y coordinates"""
        for table in tables:
            # Find questions on same page above the table
            page_questions = [q for q in questions 
                            if q['page'] == table['page_number'] and q['y_coordinate'] < table['y_coordinate']]
            
            if page_questions:
                # Get closest question above
                closest_question = max(page_questions, key=lambda q: q['y_coordinate'])
                table['linked_question'] = closest_question['question_number']
                logger.info(f"Linked {table['filename']} to question '{closest_question['question_number']}'")
            else:
                table['linked_question'] = None
                logger.warning(f"No question found for {table['filename']}")
        
        return tables
