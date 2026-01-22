"""Simple TextExtractor for PDF question extraction with asset linking."""

import fitz  # PyMuPDF
import pdfplumber
import re
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from state import Question, Subpart, MCQOption, Asset
from coordinate_image_mapper import extract_images_with_metadata, map_images_to_questions_for_pdf
from output_manager import OutputManager
import json

# Import LaTeX utilities
from latex_utils import detect_latex, render_latex

class TextExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pdf_name = os.path.basename(pdf_path)
        self.doc = None
        self.pages_text = []
        self.output_dir = "output"
        
        # Import here to avoid circular imports
        self.output_manager = OutputManager(pdf_name=self.pdf_name)
        
    def extract(self) -> List[Question]:
        """Main extraction method - returns list of Question objects"""
        # Load PDF and get text
        self._load_pdf()
        
        # Extract tables for linking
        tables = self._extract_tables()
        
        # Combine all pages into one text for cross-page question extraction
        all_text = ""
        page_boundaries = []  # Track where each page starts
        
        for page_num, page_text in enumerate(self.pages_text):
            cleaned_text = self._clean_text(page_text)
            page_boundaries.append(len(all_text))
            all_text += cleaned_text + "\n"
        
        # Extract questions from combined text
        all_questions = self._extract_questions_from_combined_text(all_text, page_boundaries)
        
        # Link images and tables to questions using coordinate-based mapping
        self._extract_and_save_images()
        self._link_images_using_coordinate_mapper(all_questions)
        self._link_tables_sequentially(all_questions, tables)
        
        # Save results using OutputManager
        all_questions = self._merge_results(all_questions, str(self.output_manager.images_dir / "image_question_mappings.json"))
        self._save_results(all_questions)
        
        return all_questions
    
    def _save_results(self, questions: List[Question]) -> Dict[str, str]:
        """Save extraction results and return output paths"""
        import json
        
        # Convert questions to dict format for JSON serialization
        questions_data = []
        for q in questions:
            question_dict = {
                'question_number': q.question_number,
                'question_text': q.question_text,
                'question_latex': getattr(q, 'question_latex', None),
                'question_type': q.question_type,
                'pdf_page': q.pdf_page,
                'subparts': [
                    {
                        'subpart_number': sp.subpart_number,
                        'subpart_text': sp.subpart_text,
                        'subpart_latex': getattr(sp, 'subpart_latex', None),
                        'question_type': sp.question_type
                    } for sp in q.subparts
                ],
                'mcq_options': [
                    {
                        'option_letter': opt.option_letter,
                        'option_text': opt.option_text
                    } for opt in q.mcq_options
                ],
                'assets': [
                    {
                        'asset_type': asset.asset_type,
                        'asset_path': asset.asset_path,
                        'page_number': asset.page_number,
                        'bbox': asset.bbox,
                        'asset_description': asset.asset_description
                    } for asset in q.assets
                ]
            }
            questions_data.append(question_dict)
        
        # Save extraction results
        pdf_name_clean = os.path.splitext(self.pdf_name)[0]
        
        extraction_path = self.output_manager.json_dir / f"{pdf_name_clean}_text_extraction.json"
        with open(extraction_path, 'w') as f:
            json.dump({
                'pdf_path': self.pdf_path,
                'extraction_type': 'text-focused',
                'questions': questions_data,
                'summary': {
                    'total_questions': len(questions_data),
                    'total_subparts': sum(len(q['subparts']) for q in questions_data),
                    'total_assets': sum(len(q['assets']) for q in questions_data)
                }
            }, f, indent=2, default=str)
        
        # Store output paths for orchestrator
        self.output_paths = {
            'extraction_results': str(extraction_path),
            'merged_state': str(extraction_path)  # Same file for text extraction
        }
        
        return self.output_paths
    
    def _load_pdf(self):
        """Load PDF and extract text by pages"""
        self.doc = fitz.open(self.pdf_path)
        self.pages_text = []
        
        for page in self.doc:
            page_text = page.get_text()
            self.pages_text.append(page_text)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize PDF text"""
        # Remove common headers/footers
        text = re.sub(r'\b(Unit 1: Sequences and Series Review|Page \d+)\b', '', text, flags=re.IGNORECASE)
        
        # Normalize line breaks and whitespace
        text = re.sub(r'\r\n|\r', '\n', text)  # Normalize line endings
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
        
        # Split into lines and clean each line
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line:  # Only keep non-empty lines
                lines.append(line)
        
        # Join back with single newlines
        text = '\n'.join(lines)
        
        # Remove excessive newlines (more aggressive)
        text = re.sub(r'\n{2,}', '\n', text)
        
        return text.strip()
    
    def _extract_questions_from_combined_text(self, all_text: str, page_boundaries: List[int]) -> List[Question]:
        """Extract questions from combined text across all pages"""
        questions = []
        
        # Question patterns: "1.", "Question 1", "Practice Example 1"
        question_patterns = [
            r'^\d+\.',  # "1.", "2.", etc.
            r'^Question\s+\d+',  # "Question 1", "Question 2"
            r'^Practice\s+Example\s+\d+',  # "Practice Example 1"
        ]
        
        # Split text into question blocks (now across all pages)
        question_blocks = self._split_into_question_blocks(all_text, question_patterns)
        
        for block_text, question_number in question_blocks:
            # Determine which page this question starts on
            question_start_pos = all_text.find(block_text)
            page_num = 1  # Default to page 1
            
            for i, boundary in enumerate(page_boundaries):
                if question_start_pos >= boundary:
                    page_num = i + 1
                else:
                    break
            
            question = self._create_question_object(block_text, question_number, page_num)
            if question:
                questions.append(question)
        
        return questions
    
    def _extract_questions_from_text(self, text: str, page_num: int) -> List[Question]:
        """Extract questions from cleaned text"""
        questions = []
        
        # Question patterns: "1.", "Question 1", "Practice Example 1"
        question_patterns = [
            r'^\d+\.',  # "1.", "2.", etc.
            r'^Question\s+\d+',  # "Question 1", "Question 2"
            r'^Practice\s+Example\s+\d+',  # "Practice Example 1"
        ]
        
        # Split text into question blocks
        question_blocks = self._split_into_question_blocks(text, question_patterns)
        
        for block_text, question_number in question_blocks:
            question = self._create_question_object(block_text, question_number, page_num)
            if question:
                questions.append(question)
        
        return questions
    
    def _split_into_question_blocks(self, text: str, patterns: List[str]) -> List[Tuple[str, str]]:
        """Split text into question blocks based on patterns"""
        blocks = []
        
        # Combine all patterns
        combined_pattern = '|'.join(f'({pattern})' for pattern in patterns)
        
        # Find all question starts
        matches = list(re.finditer(combined_pattern, text, re.MULTILINE))
        
        print(f"QUESTION SPLITTING - Found {len(matches)} question matches")
        
        for i, match in enumerate(matches):
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            
            question_text = text[start_pos:end_pos].strip()
            question_number = match.group().strip()
            
            print(f"Question block {i+1}: {question_number}")
            print(f"  Text preview: {question_text[:100]}...")
            
            blocks.append((question_text, question_number))
        
        return blocks
    
    def _create_question_object(self, text: str, question_number: str, page_num: int) -> Optional[Question]:
        """Create Question object from text block (no normalization of question_number)."""
        print(f"Creating question object for {question_number} on page {page_num}")

        question = Question()
        question.question_number = question_number
        question.pdf_page = page_num
        question.subparts = []
        question.mcq_options = []
        question.assets = []
        question.tables = []

        # Extract main question text
        main_text, remaining_text = self._extract_main_question_text(text)
        question.question_text = main_text

        print(f"Main text: {repr(main_text)}")
        print(f"Remaining text for subparts: {repr(remaining_text)}")


        # Always extract subparts first
        subparts = self._extract_subparts(remaining_text)
        for subpart in subparts:
            if detect_latex(subpart.subpart_text):
                subpart.subpart_latex = render_latex(subpart.subpart_text)
            else:
                subpart.subpart_latex = None
            question.subparts.append(subpart)

        # Handle LaTeX for main question
        if detect_latex(main_text):
            question.question_latex = render_latex(main_text)
            question.question_display = "latex"
        else:
            question.question_display = "text"
            question.question_latex = None

        print(f"Question {question_number}: Found {len(subparts)} subparts")

        # Extract MCQ options
        mcq_options = self._extract_mcq_options(remaining_text)
        for option in mcq_options:
            question.mcq_options.append(option)

        # Set flags
        question.subpart_flag = "Yes" if question.subparts else "No"
        question.mcq_flag = "Yes" if question.mcq_options else "No"

        # Classify question type
        question.question_type = self._classify_question_type(text)

        return question
    
    def _extract_main_question_text(self, text: str) -> Tuple[str, str]:
        """Separate main question from subparts/options"""
        # Look for subpart patterns: "a.", "(i)", "A:"
        subpart_pattern = r'\n(?:[a-z]\.|[A-E]:|\([ivx]+\)|\([a-z]\))'
        
        match = re.search(subpart_pattern, text)
        if match:
            main_text = text[:match.start()].strip()
            remaining_text = text[match.start():].strip()
        else:
            main_text = text.strip()
            remaining_text = ""
        
        return main_text, remaining_text
    
    def _extract_subparts(self, text: str) -> List[Subpart]:
        """Extract subparts: 'a.', '(i)', 'A:' patterns"""
        subparts = []
        
        # Log the raw text for debugging
        print(f"SUBPART EXTRACTION - Raw text: {repr(text)}")
        
        # Split text by lines to process line by line
        lines = text.split('\n')
        current_subpart = None
        
        print(f"SUBPART EXTRACTION - Processing {len(lines)} lines:")
        for i, line in enumerate(lines):
            line = line.strip()
            print(f"  Line {i}: '{line}'")
            
            if not line:
                continue
                
            # Check for subpart patterns at start of line
            subpart_match = re.match(r'^([a-z]\.|\([ivx]+\)|\([a-z]\))\s*(.*)$', line)
            
            if subpart_match:
                print(f"    -> FOUND SUBPART: {subpart_match.group(1)}")
                # Save previous subpart if exists
                if current_subpart:
                    subparts.append(current_subpart)
                
                # Start new subpart
                current_subpart = Subpart()
                current_subpart.subpart_number = subpart_match.group(1)
                current_subpart.subpart_text = subpart_match.group(2).strip()
                current_subpart.assets = []
                current_subpart.mcq_options = []
                
            elif current_subpart and line:
                print(f"    -> Continuing subpart text")
                # Continue previous subpart text
                if current_subpart.subpart_text:
                    current_subpart.subpart_text += " " + line
                else:
                    current_subpart.subpart_text = line
        
        # Don't forget the last subpart
        if current_subpart:
            subparts.append(current_subpart)
        
        print(f"SUBPART EXTRACTION - Final count: {len(subparts)} subparts")
        for i, sp in enumerate(subparts):
            print(f"  Subpart {i+1}: {sp.subpart_number} - '{sp.subpart_text}'")
        
            
            # Process question types only (LaTeX handled in _create_question_object)
            for subpart in subparts:
                subpart.question_type = self._classify_question_type(subpart.subpart_text)
        
        return subparts
    
    def _extract_mcq_options(self, text: str) -> List[MCQOption]:
        """Extract MCQ options: 'A:', 'B:', 'C:' patterns"""
        options = []
        
        # MCQ option pattern
        pattern = r'([A-E]):[\s]*(.+?)(?=\n[A-E]:|$)'
        matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
        
        for match in matches:
            option = MCQOption()
            option.option_letter = match[0]
            option.option_text = match[1].strip()
            options.append(option)
        
        return options
    

    
    def _classify_question_type(self, text: str) -> str:
        """Classify question type: evaluate|mcq|short_answer|misc"""
        text_lower = text.lower()
        
        # MCQ indicators
        if re.search(r'[A-E]:', text) or 'choose' in text_lower or 'select' in text_lower:
            return 'mcq'
        
        # Evaluation indicators
        if any(word in text_lower for word in ['evaluate', 'calculate', 'find', 'determine', 'solve']):
            return 'evaluate'
        
        # Short answer indicators
        if any(word in text_lower for word in ['explain', 'describe', 'define', 'state']):
            return 'short_answer'
        
        return 'misc'
    
    
    def _extract_and_save_images(self) -> List[Dict]:
        """Extract images from PDF and save them to designated directory"""
        extract_images_with_metadata(
            pdf_path=self.pdf_path,
            output_dir=str(self.output_manager.images_dir),
            output_json_path=str(self.output_manager.images_dir / "extraction_results.json")
        )


    def _link_images_using_coordinate_mapper(self, questions: List[Question]):
        map_images_to_questions_for_pdf(
            pdf_path=self.pdf_path,
            extracted_images_path=str(self.output_manager.images_dir / "extraction_results.json"),
            output_path=str(self.output_manager.images_dir / "image_question_mappings.json"),
        )
    
    def _extract_tables(self) -> List[Dict]:
        """Extract tables from PDF using pdfplumber and save to assets directory"""
        tables = []
        
        print(f"TABLE EXTRACTION - Starting table extraction from {self.pdf_path}")
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()
                
                print(f"TABLE EXTRACTION - Page {page_num + 1}: Found {len(page_tables)} tables")
                
                for table_index, table_data in enumerate(page_tables):
                    if table_data and len(table_data) > 0:
                        # Save table as JSON to assets directory
                        table_filename = f"page{page_num+1}_table{table_index+1}.json"
                        table_path = self.output_manager.images_dir / table_filename
                        
                        # Clean table data (remove None values)
                        cleaned_table = []
                        for row in table_data:
                            cleaned_row = [cell.strip() if cell else "" for cell in row]
                            cleaned_table.append(cleaned_row)
                        
                        # Save table data
                        with open(table_path, 'w', encoding='utf-8') as f:
                            json.dump({
                                'table_data': cleaned_table,
                                'rows': len(cleaned_table),
                                'columns': len(cleaned_table[0]) if cleaned_table else 0,
                                'page_number': page_num + 1,
                                'table_index': table_index + 1
                            }, f, indent=2, ensure_ascii=False)
                        
                        print(f"Saved table: {table_path}")
                        
                        # Get table bounding box if available
                        table_bbox = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
                        try:
                            # Try to get table bbox from pdfplumber
                            tables_with_bbox = page.find_tables()
                            if table_index < len(tables_with_bbox):
                                bbox = tables_with_bbox[table_index].bbox
                                table_bbox = {
                                    'x': bbox[0],
                                    'y': bbox[1], 
                                    'width': bbox[2] - bbox[0],
                                    'height': bbox[3] - bbox[1]
                                }
                        except Exception as e:
                            print(f"Could not get table bbox: {e}")
                        
                        tables.append({
                            'path': str(table_path),
                            'filename': table_filename,
                            'page_number': page_num + 1,
                            'table_index': table_index + 1,
                            'rows': len(cleaned_table),
                            'columns': len(cleaned_table[0]) if cleaned_table else 0,
                            'bbox': table_bbox,
                            'data_preview': cleaned_table[:3] if len(cleaned_table) > 3 else cleaned_table  # First 3 rows
                        })
                        
                        print(f"  Table {table_index + 1}: {len(cleaned_table)} rows x {len(cleaned_table[0]) if cleaned_table else 0} columns")
        
        print(f"TABLE EXTRACTION - Total tables extracted: {len(tables)}")
        return tables
    
    def _link_tables_sequentially(self, questions: List[Question], tables: List[Dict]):
        """Link tables to questions based on proximity and context"""
        print(f"TABLE LINKING - Linking {len(tables)} tables to {len(questions)} questions")
        
        # Sort questions by page and position for better matching
        questions_sorted = sorted(questions, key=lambda q: (q.pdf_page, q.question_number))
        
        for table in tables:
            table_page = table['page_number']
            table_y = table['bbox']['y'] if table['bbox']['y'] > 0 else float('inf')
            
            # Find questions on the same page
            page_questions = [q for q in questions_sorted if q.pdf_page == table_page]
            
            if not page_questions:
                print(f"  Table on page {table_page}: No questions found on this page")
                continue
            
            # Strategy: Link table to the closest question above it, or the first question if no question is above
            best_question = None
            min_distance = float('inf')
            
            # If we have bbox info, use position-based linking
            if table_y != float('inf'):
                for question in page_questions:
                    # Assume questions appear before tables they reference
                    # Link to the closest question that appears before the table
                    question_position = self._estimate_question_position(question, table_page)
                    
                    if question_position <= table_y:  # Question is above table
                        distance = table_y - question_position
                        if distance < min_distance:
                            min_distance = distance
                            best_question = question
                
                # If no question found above, link to first question on page
                if not best_question and page_questions:
                    best_question = page_questions[0]
            else:
                # No bbox info - use simple heuristic based on question numbers
                # Link to the highest numbered question on the page (likely closest to table)
                best_question = max(page_questions, key=lambda q: self._extract_question_number(q.question_number))
            
            if best_question:
                asset = Asset()
                asset.asset_type = "table"
                asset.asset_path = table['path']
                asset.asset_description = f"Table with {table['rows']} rows and {table['columns']} columns"
                asset.bbox = table['bbox']
                asset.page_number = table['page_number']
                
                best_question.tables.append(asset)
                print(f"  Table on page {table_page}: Linked to Question {best_question.question_number}")
            else:
                print(f"  Table on page {table_page}: Could not find suitable question to link")
    
    def _estimate_question_position(self, question: Question, page_num: int) -> float:
        """Estimate vertical position of question on page (simple heuristic)"""
        # Simple heuristic: assume questions are ordered by their number
        question_num = self._extract_question_number(question.question_number)
        # Assume each question takes about 100 points of vertical space
        return question_num * 100
    
    def _extract_question_number(self, question_number_str: str) -> int:
        """Extract numeric part from question number string"""
        match = re.search(r'(\d+)', question_number_str)
        return int(match.group(1)) if match else 0

    
    def _merge_results(self, all_questions: List[Question], image_question_mappings_path: str) -> List[Question]:
        """
        Update each Question object's assets field using image-question mappings and return updated list.
        Uses containment-based matching: TextExtractor question_number should be contained within
        CoordinateImageMapper question_number (which is the full line text).
        """
        import json
        if not all_questions or not image_question_mappings_path:
            return all_questions

        # Load image-question mappings
        try:
            with open(image_question_mappings_path, 'r') as f:
                mapping_json = json.load(f)
        except Exception as e:
            print(f"Could not load image-question mappings: {e}")
            return all_questions

        print(f"MERGE RESULTS - Processing {len(all_questions)} questions with {len(mapping_json.get('mappings', []))} image mappings")

        # Update each Question object's assets using containment-based matching
        for q in all_questions:
            page = getattr(q, 'pdf_page', None)
            text_extractor_qnum = str(getattr(q, 'question_number', None))
            
            print(f"MERGE - Looking for matches for Question '{text_extractor_qnum}' on page {page}")
            
            # Find matching images for this question using containment logic
            matching_images = []
            for mapping in mapping_json.get('mappings', []):
                image_mapper_qnum = str(mapping['question']['question_number'])
                mapping_page = mapping['question']['page']
                
                # Check if text extractor question is contained in image mapper question
                # and they're on the same page
                if (mapping_page == page and 
                    text_extractor_qnum.strip() in image_mapper_qnum.strip()):
                    
                    matching_images.append(mapping['image'])
                    print(f"  MATCH FOUND: '{text_extractor_qnum}' contained in '{image_mapper_qnum}'")
                    print(f"    Image: {mapping['image']['filename']}")
            
            # Convert matching images to Asset objects
            assets = []
            for img in matching_images:
                # Asset expects: asset_type, asset_path, asset_description, bbox, page_number
                asset = Asset()
                asset.asset_type = 'image'
                asset.asset_path = img.get('filepath')
                asset.asset_description = f"Image mapped to question {text_extractor_qnum}"
                
                # Use coordinates as bbox if available, else fallback to x0/y0/x1/y1
                if 'coordinates' in img:
                    coords = img['coordinates']
                    asset.bbox = {
                        'x0': coords.get('x0', 0),
                        'y0': coords.get('y0', 0),
                        'x1': coords.get('x1', 0),
                        'y1': coords.get('y1', 0),
                        'center_x': coords.get('center_x', 0),
                        'center_y': coords.get('center_y', 0)
                    }
                else:
                    asset.bbox = {
                        'x0': 0, 'y0': 0, 'x1': img.get('width', 0), 'y1': img.get('height', 0),
                        'center_x': img.get('width', 0) / 2, 'center_y': img.get('height', 0) / 2
                    }
                asset.page_number = img.get('page')
                assets.append(asset)
            
            q.assets = assets
            print(f"  FINAL: Question '{text_extractor_qnum}' assigned {len(assets)} images")
        
        print(f"MERGE RESULTS - Completed merging for all questions")
        return all_questions
