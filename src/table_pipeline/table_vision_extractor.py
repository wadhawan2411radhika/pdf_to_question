"""
Table Vision Extractor

Combines table extraction with image mapping and LLM vision analysis.
Integrates multiple modalities for comprehensive question extraction.
"""

import os
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

from src.table_pipeline.image_tablecell_mapper import ImageTableCellMapper
from src.table_pipeline.table_text_extractor import TableTextExtractor
from src.llm_service import LLMService
from src.output_manager import OutputManager
from src.state import Question, Subpart, MCQOption, Asset, DocumentMetadata, ExtractionStats, OutputState

logger = logging.getLogger(__name__)


class TableVisionExtractor:
    """Extractor that combines table extraction, image mapping, and vision analysis"""
    
    def __init__(self, pdf_path: str, output_dir: str = "output"):
        self.pdf_path = pdf_path
        self.pdf_name = os.path.basename(pdf_path)
        try: 
            self.llm_service = LLMService()
        except Exception as e:
            logger.error(f"Failed to initialise LLM Service: {e}")
            self.llm_service = None
        self.output_manager = OutputManager(base_output_dir=output_dir, pdf_name=self.pdf_name)
        
        logger.info(f"TableVisionExtractor initialized for {pdf_path}")
        logger.info(f"Output will be saved to: {self.output_manager.pdf_output_dir}")
    
    def extract_questions(self) -> Dict[str, Any]:
        """Main extraction method"""
        logger.info("Starting enhanced extraction process")
        
        # Step 1: Extract table questions
        logger.info("Step 1: Extracting table questions")
        table_extractor = TableTextExtractor()
        table_questions = table_extractor.extract_questions_from_table(self.pdf_path)
        logger.info(f"Extracted {len(table_questions)} table questions")
        
        # Step 2: Map images to cells (pass output manager for consistent paths)
        logger.info("Step 2: Mapping images to table cells")
        image_mapper = ImageTableCellMapper(self.pdf_path, output_manager=self.output_manager)
        image_results = image_mapper.map_images_to_cells()
        logger.info(f"Found {image_results['total_images']} images, created {image_results['total_mappings']} mappings")
        
        # Step 3: Analyze images with LLM
        vision_analysis = {}
        if self.llm_service:
            logger.info("Step 3: Starting LLM vision analysis")
            
            for i, mapping in enumerate(image_results['mappings']):
                image_path = mapping['image']['file_path']
                if os.path.exists(image_path):
                    try:
                        logger.debug(f"Analyzing image {i+1}/{len(image_results['mappings'])}: {image_path}")
                        result = self.llm_service.analyze_image(image_path)
                        vision_analysis[image_path] = {
                            'question_text': result.question_text,
                            'mcq_options': result.mcq_options,
                            'has_diagram': result.has_diagram,
                        }
                        logger.debug(f"Vision analysis completed for {image_path}")
                    except Exception as e:
                        logger.error(f"Vision analysis error for {image_path}: {e}")
                else:
                    logger.warning(f"Image file not found: {image_path}")
            
            logger.info(f"Completed vision analysis for {len(vision_analysis)} images")
        else:
            logger.warning("LLM Service is not available. Skipping the vision analysis for images")
        
        # Step 4: Combine everything
        logger.info("Step 4: Combining results and creating merged state")
        combined_results = {
            'pdf_path': self.pdf_path,
            'table_questions': table_questions,
            'image_mappings': image_results['mappings'],
            'vision_analysis': vision_analysis,
            'summary': {
                'total_table_questions': len(table_questions),
                'total_images': image_results['total_images'],
                'total_mappings': image_results['total_mappings'],
                'total_vision_analyses': len(vision_analysis)
            }
        }
        
        # Create merged state format
        logger.info("Creating merged state format")
        merged_state = self._create_merged_state(combined_results)
        logger.info(f"Created merged state with {len(merged_state['questions'])} questions")
        
        # Save using OutputManager
        pdf_name_clean = os.path.splitext(self.pdf_name)[0]
        
        # Save extraction results
        extraction_path = self.output_manager.json_dir / f"{pdf_name_clean}_extraction_results.json"
        with open(extraction_path, 'w') as f:
            json.dump(combined_results, f, indent=2, default=str)
        logger.info(f"Extraction results saved to: {extraction_path}")
        
        # Save merged state using proper schema
        merged_path = self.output_manager.json_dir / f"{pdf_name_clean}_merged_state.json"
        schema_output = self._save_results_with_schema(combined_results, merged_path)
        logger.info(f"Merged state saved to: {merged_path}")
        
        # Store paths for orchestrator access
        combined_results['output_paths'] = {
            'extraction_results': str(extraction_path),
            'merged_state': str(merged_path)
        }
        
        logger.info("Enhanced extraction process completed successfully")
        return combined_results
    
    def _save_results_with_schema(self, results: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """Save results using proper OutputState schema - similar to TextExtractor approach"""
        import fitz
        
        # Get total pages from PDF
        total_pages = 0
        try:
            with fitz.open(self.pdf_path) as doc:
                total_pages = len(doc.pages)
        except Exception as e:
            logger.warning(f"Could not get page count: {e}")
            total_pages = 1
        
        # Create DocumentMetadata
        doc_metadata = DocumentMetadata()
        doc_metadata.pdf_name = self.pdf_name
        doc_metadata.pdf_path = self.pdf_path
        doc_metadata.total_pages = total_pages
        doc_metadata.processing_timestamp = datetime.now().isoformat()
        doc_metadata.processing_time_seconds = 0.0  # Will be set by orchestrator
        doc_metadata.dominance_type = "table-dominant"
        doc_metadata.extraction_method = "TableVisionExtractor"
        
        # Convert table results to Question objects
        questions = self._convert_to_question_objects(results)
        
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
        
        # Convert to dict for JSON serialization (same as TextExtractor)
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
        
        # Save to file
        with open(output_path, 'w') as f:
            json.dump(output_dict, f, indent=2, default=str)
        
        return output_dict
    
    def _convert_to_question_objects(self, results: Dict[str, Any]) -> List[Question]:
        """Convert table results to Question objects"""
        questions = []
        processed_question_ids = set()
        
        for table_q in results['table_questions']:
            question_num = table_q['question_num']
            
            # Find images for this question and determine the page
            question_assets = []
            vision_text = ""
            mcq_options_data = []
            question_page = 1  # Default page
            
            # Find matching image mappings
            matching_mappings = []
            for mapping in results['image_mappings']:
                if mapping['cell']['text'] == question_num:
                    matching_mappings.append(mapping)
            
            # Process image mappings
            if matching_mappings:
                question_page = matching_mappings[0]['cell']['page']
                
                for mapping in matching_mappings:
                    if mapping['cell']['page'] == question_page:
                        image_path = mapping['image']['file_path']
                        
                        # Create Asset object
                        asset = Asset()
                        asset.asset_type = 'image'
                        asset.asset_path = image_path
                        asset.asset_description = f"Image mapped to question {question_num}"
                        asset.bbox = mapping['image']['bbox']
                        asset.page_number = mapping['cell']['page']
                        question_assets.append(asset)
                        
                        # Get vision analysis
                        if image_path in results['vision_analysis']:
                            vision_data = results['vision_analysis'][image_path]
                            if vision_data.get('question_text'):
                                vision_text = vision_data['question_text']
                            if vision_data.get('mcq_options'):
                                mcq_options_data = vision_data['mcq_options']
            
            # Create unique question ID
            unique_question_id = f"page{question_page}_question{question_num}"
            original_id = unique_question_id
            suffix = 1
            while unique_question_id in processed_question_ids:
                unique_question_id = f"{original_id}_{suffix}"
                suffix += 1
            processed_question_ids.add(unique_question_id)
            
            # Create MCQOption objects
            mcq_options = []
            if table_q.get('mcq_options'):
                for opt in table_q['mcq_options']:
                    mcq_option = MCQOption()
                    mcq_option.option_letter = opt['letter']
                    mcq_option.option_text = opt['text']
                    mcq_options.append(mcq_option)
            
            if mcq_options_data:
                existing_letters = [opt.option_letter for opt in mcq_options]
                for vision_opt in mcq_options_data:
                    if vision_opt['letter'] not in existing_letters:
                        mcq_option = MCQOption()
                        mcq_option.option_letter = vision_opt['letter']
                        mcq_option.option_text = vision_opt['text']
                        mcq_options.append(mcq_option)
            
            # Create Question object
            question = Question()
            question.question_number = unique_question_id
            question.question_text = table_q['question_text'] or vision_text
            question.question_latex = None  # No LaTeX processing yet
            question.question_type = 'mcq' if mcq_options else 'evaluate'
            question.pdf_page = question_page
            question.subpart_flag = False  # No subparts in table extractor yet
            question.mcq_flag = bool(mcq_options)
            question.subparts = []  # No subparts yet
            question.mcq_options = mcq_options
            question.assets = question_assets
            
            questions.append(question)
        
        return questions
    
    def _create_merged_state(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Simple merger to state.py format"""
        
        # Create question mapping with page context
        questions = []
        processed_question_ids = set()
        
        for table_q in results['table_questions']:
            question_num = table_q['question_num']
            
            # Find images for this question and determine the page
            question_images = []
            vision_text = ""
            mcq_options = []
            question_page = 1  # Default page
            
            # First pass: find images that match this question number
            matching_mappings = []
            for mapping in results['image_mappings']:
                if mapping['cell']['text'] == question_num:
                    matching_mappings.append(mapping)
            
            # If we have mappings, use the first one's page as the question page
            if matching_mappings:
                question_page = matching_mappings[0]['cell']['page']
                
                # Only use images from the same page as the first match
                for mapping in matching_mappings:
                    if mapping['cell']['page'] == question_page:
                        page = mapping['cell']['page']
                        image_path = mapping['image']['file_path']
                        
                        # Add image as asset
                        question_images.append({
                            'asset_type': 'image',
                            'asset_path': image_path,
                            'bbox': mapping['image']['bbox'],
                            'page_number': page
                        })
                        
                        # Get vision analysis
                        if image_path in results['vision_analysis']:
                            vision_data = results['vision_analysis'][image_path]
                            if vision_data.get('question_text'):
                                vision_text = vision_data['question_text']
                            if vision_data.get('mcq_options'):
                                mcq_options = vision_data['mcq_options']
            
            # Create unique question ID with page context
            unique_question_id = f"page{question_page}_question{question_num}"
            
            # Handle duplicates by adding suffix
            original_id = unique_question_id
            suffix = 1
            while unique_question_id in processed_question_ids:
                unique_question_id = f"{original_id}_{suffix}"
                suffix += 1
            
            processed_question_ids.add(unique_question_id)
            
            # Combine MCQ options from table and vision
            all_mcq_options = []
            
            # First add MCQ options from table extraction
            if table_q.get('mcq_options'):
                all_mcq_options.extend(table_q['mcq_options'])
            
            # Then add MCQ options from vision (if not already present)
            if mcq_options:
                for vision_opt in mcq_options:
                    # Check if this option letter already exists from table
                    existing_letters = [opt['letter'] for opt in all_mcq_options]
                    if vision_opt['letter'] not in existing_letters:
                        all_mcq_options.append(vision_opt)
            
            # Create question object
            question = {
                'question_number': unique_question_id,
                'question_text': table_q['question_text'] or vision_text,
                'question_type': 'MCQ' if all_mcq_options else 'descriptive',
                'mcq_options': all_mcq_options,
                'assets': question_images,
                'answer': table_q.get('answer', ''),
                'page_number': question_page,
                'vision_metadata': {'vision_question_text': vision_text}
            }
            
            questions.append(question)
        
        # Simple merged state
        merged_state = {
            'pdf_path': results['pdf_path'],
            'questions': questions,
            'summary': {
                'total_questions': len(questions),
                'mcq_questions': len([q for q in questions if q['question_type'] == 'MCQ']),
                'total_assets': sum(len(q['assets']) for q in questions)
            }
        }
        
        return merged_state
