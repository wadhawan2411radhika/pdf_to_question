from typing import List

class DocumentMetadata:
    """
    This class defines the structure for storing metadata about the processed PDF document.
    """
    pdf_name: str
    pdf_path: str
    total_pages: int
    processing_timestamp: str
    processing_time_seconds: float
    dominance_type: str
    extraction_method: str

class MCQOption:
    """
    This class defines the structure for storing information about each multiple-choice question (MCQ) option.
    """
    option_letter: str
    option_text: str
    
class Asset:
    """
    This class defines the structure for storing information about each asset (image, table, figure) associated with a question.
    """
    asset_type: str
    asset_path: str
    asset_description: str | None
    bbox: dict
    page_number: int

class Subpart:
    """
    This class defines the structure for storing information about each subpart of a question.
    """
    subpart_number: str
    subpart_text: str
    subpart_latex: str | None
    question_type: str
    assets: list
    mcq_options: list

class Question:
    """
    This class defines the structure for storing information about each extracted question from the PDF.
    """
    question_number: str
    question_type: str
    question_text: str
    question_latex: str | None
    pdf_page: int
    subpart_flag: bool
    mcq_flag: bool
    subparts: List[Subpart]
    mcq_options: List[MCQOption]
    assets: List[Asset]
    tables: List[Asset]

class ExtractionStats:
    """
    This class defines the structure for storing extraction statistics.
    """
    total_questions: int
    mcq_count: int
    subpart_count: int
    images_extracted: int
    tables_extracted: int
    processing_errors: list

class OutputState:
    """
    This class defines the structure for storing the state of the PDF extraction process.
    """
    document_metadata: DocumentMetadata
    questions: List[Question]
    extraction_stats: ExtractionStats

