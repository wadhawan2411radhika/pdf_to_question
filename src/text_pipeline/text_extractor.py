"""Simple TextExtractor for PDF question extraction with asset linking."""

import fitz  # PyMuPDF
import re
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from src.state import Question, Subpart, MCQOption, Asset, DocumentMetadata, ExtractionStats, OutputState
from src.text_pipeline.coordinate_image_mapper import extract_images_with_metadata, map_images_to_questions_for_pdf
from src.text_pipeline.coordinate_table_mapper import CoordinateTableMapper
from src.output_manager import OutputManager

# Import LaTeX utilities
from src.text_pipeline.latex_utils import detect_latex, render_latex

logger = logging.getLogger(__name__)

class TextExtractor:
    def __init__(self, pdf_path: str, output_dir: str = "output"):
        self.pdf_path = pdf_path
        self.pdf_name = os.path.basename(pdf_path)
        self.doc = None
        self.pages_text = []
        self.output_dir = output_dir
        
        # Import here to avoid circular imports
        self.output_manager = OutputManager(base_output_dir=output_dir, pdf_name=self.pdf_name)
        
    def extract(self) -> List[Question]:
        """Main extraction method - returns list of Question objects"""
        # Load PDF and get text
        self._load_pdf()
        
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
        self._link_tables_using_coordinate_mapper(all_questions)
        
        # Save results using OutputManager
        all_questions = self._merge_results(all_questions, str(self.output_manager.images_dir / "image_question_mappings.json"))
        self._save_results(all_questions)
        
        return all_questions
    
    def _save_results(self, questions: List[Question]) -> Dict[str, str]:
        """Save extraction results using proper OutputState schema and return output paths"""
        import json
        from datetime import datetime
        
        # Create DocumentMetadata
        doc_metadata = DocumentMetadata()
        doc_metadata.pdf_name = self.pdf_name
        doc_metadata.pdf_path = self.pdf_path
        doc_metadata.total_pages = len(self.pages_text)
        doc_metadata.processing_timestamp = datetime.now().isoformat()
        doc_metadata.processing_time_seconds = 0.0  # Will be set by orchestrator
        doc_metadata.dominance_type = "text-dominant"
        doc_metadata.extraction_method = "TextExtractor"
        
        # Create ExtractionStats
        extraction_stats = ExtractionStats()
        extraction_stats.total_questions = len(questions)
        extraction_stats.mcq_count = len([q for q in questions if q.mcq_options])
        extraction_stats.subpart_count = sum(len(q.subparts) for q in questions)
        extraction_stats.images_extracted = sum(len([a for a in q.assets if a.asset_type == 'image']) for q in questions)
        extraction_stats.tables_extracted = sum(len([a for a in q.assets if a.asset_type == 'table']) for q in questions)
        extraction_stats.processing_errors = []  # No errors tracked yet
        
        # Create OutputState
        output_state = OutputState()
        output_state.document_metadata = doc_metadata
        output_state.questions = questions
        output_state.extraction_stats = extraction_stats
        
        # Convert to dict for JSON serialization
        output_dict = {
            'document_metadata': {
                'pdf_name': doc_metadata.pdf_name,
                'pdf_path': doc_metadata.pdf_path,
                'total_pages': doc_metadata.total_pages,
                'processing_timestamp': doc_metadata.processing_timestamp,
                'processing_time_seconds': doc_metadata.processing_time_seconds,
                'dominance_type': doc_metadata.dominance_type,
                'extraction_method': doc_metadata.extraction_method
            },
            'questions': [
                {
                    'question_number': q.question_number,
                    'question_text': q.question_text,
                    'question_latex': getattr(q, 'question_latex', None),
                    'question_type': q.question_type,
                    'pdf_page': q.pdf_page,
                    'subpart_flag': q.subpart_flag,
                    'mcq_flag': q.mcq_flag,
                    'subparts': [
                        {
                            'subpart_number': sp.subpart_number,
                            'subpart_text': sp.subpart_text,
                            'subpart_latex': getattr(sp, 'subpart_latex', None),
                            'question_type': sp.question_type,
                            'assets': sp.assets,
                            'mcq_options': sp.mcq_options
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
                            'asset_description': asset.asset_description,
                            'bbox': asset.bbox,
                            'page_number': asset.page_number
                        } for asset in q.assets
                    ]
                } for q in questions
            ],
            'extraction_stats': {
                'total_questions': extraction_stats.total_questions,
                'mcq_count': extraction_stats.mcq_count,
                'subpart_count': extraction_stats.subpart_count,
                'images_extracted': extraction_stats.images_extracted,
                'tables_extracted': extraction_stats.tables_extracted,
                'processing_errors': extraction_stats.processing_errors
            }
        }
        
        # Save extraction results using proper schema
        pdf_name_clean = os.path.splitext(self.pdf_name)[0]
        
        extraction_path = self.output_manager.json_dir / f"{pdf_name_clean}_text_extraction.json"
        with open(extraction_path, 'w') as f:
            json.dump(output_dict, f, indent=2, default=str)
        
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
        
        logger.info(f"Found {len(matches)} question matches")
        
        for i, match in enumerate(matches):
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            
            question_text = text[start_pos:end_pos].strip()
            question_number = match.group().strip()
            
            blocks.append((question_text, question_number))
        
        return blocks
    
    def _create_question_object(self, text: str, question_number: str, page_num: int) -> Optional[Question]:
        """Create Question object from text block"""
        logger.debug(f"Creating question object for {question_number} on page {page_num}")

        question = Question()
        question.question_number = question_number
        question.pdf_page = page_num
        question.subparts = []
        question.mcq_options = []
        question.assets = []

        # Extract main question text
        main_text, remaining_text = self._extract_main_question_text(text)
        question.question_text = main_text

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
        else:
            question.question_latex = None

        logger.debug(f"Question {question_number}: Found {len(subparts)} subparts")

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
        
        if not text.strip():
            return subparts
        
        # Split text by lines to process line by line
        lines = text.split('\n')
        current_subpart = None
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
                
            # Check for subpart patterns at start of line
            subpart_match = re.match(r'^([a-z]\.|\([ivx]+\)|\([a-z]\))\s*(.*)$', line)
            
            if subpart_match:
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
                # Continue previous subpart text
                if current_subpart.subpart_text:
                    current_subpart.subpart_text += " " + line
                else:
                    current_subpart.subpart_text = line
        
        # Don't forget the last subpart
        if current_subpart:
            subparts.append(current_subpart)
        
        # Process question types only (LaTeX handled in _create_question_object)
        for subpart in subparts:
            subpart.question_type = self._classify_question_type(subpart.subpart_text)
        
        logger.debug(f"Extracted {len(subparts)} subparts")
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
    
    def _link_tables_using_coordinate_mapper(self, questions: List[Question]):
        """Link tables to questions using coordinate-based mapping"""
        table_mapper = CoordinateTableMapper(self.pdf_path, self.output_manager)
        linked_tables = table_mapper.extract_and_link_tables()
        
        # Convert linked tables to assets and add to questions using containment-based matching
        for table in linked_tables:
            if table.get('linked_question'):
                # Find the matching question using containment logic (same as image mapping)
                table_question_text = str(table['linked_question']).strip()
                
                for question in questions:
                    text_extractor_qnum = str(question.question_number).strip()
                    
                    # Use containment-based matching: TextExtractor question should be contained in table mapper question
                    if text_extractor_qnum in table_question_text:
                        asset = Asset()
                        asset.asset_type = "table"
                        asset.asset_path = table['path']
                        asset.asset_description = f"Table with {table['rows']} rows and {table['columns']} columns"
                        asset.bbox = table['bbox']
                        asset.page_number = table['page_number']
                        
                        question.assets.append(asset)
                        logger.info(f"Linked table {table['filename']} to question '{text_extractor_qnum}' using containment matching")
    

    
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
            logger.warning(f"Could not load image-question mappings: {e}")
            return all_questions

        logger.info(f"Processing {len(all_questions)} questions with {len(mapping_json.get('mappings', []))} image mappings")

        # Update each Question object's assets using containment-based matching
        for q in all_questions:
            page = getattr(q, 'pdf_page', None)
            text_extractor_qnum = str(getattr(q, 'question_number', None))
            
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
                    logger.debug(f"Match found: '{text_extractor_qnum}' -> {mapping['image']['filename']}")
            
            # Convert matching images to Asset objects
            image_assets = []
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
                image_assets.append(asset)
            
            # Preserve existing assets (tables) and append images
            existing_assets = getattr(q, 'assets', []) or []
            q.assets = existing_assets + image_assets
            if image_assets:
                logger.debug(f"Question '{text_extractor_qnum}' assigned {len(image_assets)} images (total assets: {len(q.assets)})")
        
        logger.info("Completed merging image mappings with questions")
        return all_questions
