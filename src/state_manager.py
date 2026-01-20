"""State management for PDF extraction process."""

from typing import List, Dict, Any
from datetime import datetime
import json
from state import OutputState, DocumentMetadata, ExtractionStats, Question


class StateManager:
    """Manages the creation and manipulation of OutputState objects."""
    
    def __init__(self):
        self.output_state = None
    
    def create_output_state(self, pdf_path: str, questions: List[Question], 
                          dominance: str, processing_type: str, 
                          num_pages: int) -> OutputState:
        """Create OutputState from extracted questions and metadata."""
        
        # Initialize document metadata
        doc_metadata = DocumentMetadata()
        doc_metadata.pdf_name = pdf_path.split('/')[-1]
        doc_metadata.pdf_path = pdf_path
        doc_metadata.total_pages = num_pages
        doc_metadata.processing_timestamp = datetime.now().isoformat()
        doc_metadata.processing_time_seconds = 0.0  # Will be updated later
        doc_metadata.dominance_type = dominance
        doc_metadata.extraction_method = processing_type
        
        # Calculate extraction stats
        stats = ExtractionStats()
        stats.total_questions = len(questions)
        stats.mcq_count = sum(1 for q in questions if q.mcq_flag == "Yes")
        stats.subpart_count = sum(len(q.subparts) for q in questions)
        stats.images_extracted = sum(len(q.assets) for q in questions)
        stats.tables_extracted = sum(len(q.tables) for q in questions)
        stats.processing_errors = []
        
        # Create output state
        output_state = OutputState()
        output_state.document_metadata = doc_metadata
        output_state.questions = questions
        output_state.extraction_stats = stats
        
        self.output_state = output_state
        return output_state
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert OutputState to dictionary for JSON serialization."""
        if not self.output_state:
            return {}
        
        return {
            "document_metadata": {
                "pdf_name": self.output_state.document_metadata.pdf_name,
                "pdf_path": self.output_state.document_metadata.pdf_path,
                "total_pages": self.output_state.document_metadata.total_pages,
                "processing_timestamp": self.output_state.document_metadata.processing_timestamp,
                "processing_time_seconds": self.output_state.document_metadata.processing_time_seconds,
                "dominance_type": self.output_state.document_metadata.dominance_type,
                "extraction_method": self.output_state.document_metadata.extraction_method
            },
            "questions": [self._question_to_dict(q) for q in self.output_state.questions],
            "extraction_stats": {
                "total_questions": self.output_state.extraction_stats.total_questions,
                "mcq_count": self.output_state.extraction_stats.mcq_count,
                "subpart_count": self.output_state.extraction_stats.subpart_count,
                "images_extracted": self.output_state.extraction_stats.images_extracted,
                "tables_extracted": self.output_state.extraction_stats.tables_extracted,
                "processing_errors": self.output_state.extraction_stats.processing_errors
            }
        }
    
    def _question_to_dict(self, question: Question) -> Dict[str, Any]:
        """Convert Question object to dictionary."""
        return {
            "question_number": question.question_number,
            "question_type": question.question_type,
            "question_text": question.question_text,
            "question_latex": question.question_latex,
            "question_display": question.question_display,
            "pdf_page": question.pdf_page,
            "subpart_flag": question.subpart_flag,
            "mcq_flag": question.mcq_flag,
            "subparts": [self._subpart_to_dict(sp) for sp in question.subparts],
            "mcq_options": [self._mcq_option_to_dict(opt) for opt in question.mcq_options],
            "assets": [self._asset_to_dict(asset) for asset in question.assets],
            "tables": [self._asset_to_dict(table) for table in question.tables]
        }
    
    def _subpart_to_dict(self, subpart) -> Dict[str, Any]:
        """Convert Subpart object to dictionary."""
        return {
            "subpart_number": subpart.subpart_number,
            "subpart_text": subpart.subpart_text,
            "subpart_latex": subpart.subpart_latex,
            "question_type": subpart.question_type,
            "assets": [self._asset_to_dict(asset) for asset in subpart.assets],
            "mcq_options": [self._mcq_option_to_dict(opt) for opt in subpart.mcq_options]
        }
    
    def _mcq_option_to_dict(self, option) -> Dict[str, Any]:
        """Convert MCQOption object to dictionary."""
        return {
            "option_letter": option.option_letter,
            "option_text": option.option_text
        }
    
    def _asset_to_dict(self, asset) -> Dict[str, Any]:
        """Convert Asset object to dictionary."""
        return {
            "asset_type": asset.asset_type,
            "asset_path": asset.asset_path,
            "asset_description": asset.asset_description,
            "bbox": asset.bbox,
            "page_number": asset.page_number
        }
    
    def save_to_json(self, output_path: str) -> str:
        """Save the output state to JSON file."""
        data = self.to_dict()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def update_processing_time(self, processing_time: float):
        """Update the processing time in metadata."""
        if self.output_state:
            self.output_state.document_metadata.processing_time_seconds = processing_time
    
    def add_processing_error(self, error: str):
        """Add a processing error to the stats."""
        if self.output_state:
            self.output_state.extraction_stats.processing_errors.append(error)
