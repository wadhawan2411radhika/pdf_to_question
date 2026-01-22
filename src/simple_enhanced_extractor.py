"""
Simple Enhanced Table Extractor

Combines table extraction with image mapping and basic LLM vision analysis.
Keeps it simple and extensible.
"""

import os
import json
import logging
from typing import List, Dict, Any

from simple_image_mapper import SimpleImageMapper
from table_extractor import TableExtractor
from llm_service import LLMService
from output_manager import OutputManager

logger = logging.getLogger(__name__)


class SimpleEnhancedExtractor:
    """Simple extractor that combines tables, images, and vision analysis"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pdf_name = os.path.basename(pdf_path)
        self.llm_service = LLMService()
        self.output_manager = OutputManager(pdf_name=self.pdf_name)
        
        logger.info(f"SimpleEnhancedExtractor initialized for {pdf_path}")
        logger.info(f"Output will be saved to: {self.output_manager.pdf_output_dir}")
    
    def extract_questions(self) -> Dict[str, Any]:
        """Main extraction method"""
        logger.info("Starting enhanced extraction process")
        
        # Step 1: Extract table questions
        logger.info("Step 1: Extracting table questions")
        table_extractor = TableExtractor()
        table_questions = table_extractor.extract_questions_from_table(self.pdf_path)
        logger.info(f"Extracted {len(table_questions)} table questions")
        
        # Step 2: Map images to cells (pass output manager for consistent paths)
        logger.info("Step 2: Mapping images to table cells")
        image_mapper = SimpleImageMapper(self.pdf_path, output_manager=self.output_manager)
        image_results = image_mapper.map_images_to_cells()
        logger.info(f"Found {image_results['total_images']} images, created {image_results['total_mappings']} mappings")
        
        # Step 3: Analyze images with LLM
        logger.info("Step 3: Starting LLM vision analysis")
        vision_analysis = {}
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
                        'mathematical_content': result.mathematical_content
                    }
                    logger.debug(f"Vision analysis completed for {image_path}")
                except Exception as e:
                    logger.error(f"Vision analysis error for {image_path}: {e}")
            else:
                logger.warning(f"Image file not found: {image_path}")
        
        logger.info(f"Completed vision analysis for {len(vision_analysis)} images")
        
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
        
        # Save merged state
        merged_path = self.output_manager.json_dir / f"{pdf_name_clean}_merged_state.json"
        with open(merged_path, 'w') as f:
            json.dump(merged_state, f, indent=2, default=str)
        logger.info(f"Merged state saved to: {merged_path}")
        
        # Store paths for orchestrator access
        combined_results['output_paths'] = {
            'extraction_results': str(extraction_path),
            'merged_state': str(merged_path)
        }
        
        logger.info("Enhanced extraction process completed successfully")
        return combined_results
    
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
