"""
Text Pipeline - Coordinate-based PDF extraction

This pipeline uses coordinate-based mapping to extract text, images, and tables
from PDFs using rule-based approaches.
"""

from src.text_pipeline.text_extractor import TextExtractor
from src.text_pipeline.coordinate_image_mapper import CoordinateImageMapper, extract_images_with_metadata, map_images_to_questions_for_pdf
from src.text_pipeline.coordinate_table_mapper import CoordinateTableMapper
from src.text_pipeline.latex_utils import detect_latex, render_latex

__all__ = [
    'TextExtractor',
    'CoordinateImageMapper',
    'CoordinateTableMapper',
    'extract_images_with_metadata',
    'map_images_to_questions_for_pdf',
    'detect_latex',
    'render_latex'
]
