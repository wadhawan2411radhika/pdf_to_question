"""
Coordinate-based Image-Question Mapper

Maps images to questions based on Y-coordinate positioning.
Logic: For each image, find the question that appears directly above it on the same page.
"""

import fitz  # PyMuPDF
import re
import json
import os
from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class CoordinateImageMapper:
    """
    Maps images to questions using coordinate-based positioning.
    Finds the question directly above each image on the same page.
    """
    
    def __init__(self, pdf_path: str, extracted_images_path: str = None):
        self.pdf_path = pdf_path
        self.extracted_images_path = extracted_images_path or "extracted_images/extraction_results.json"
        self.doc = None
        
    def __enter__(self):
        self.doc = fitz.open(self.pdf_path)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.doc:
            self.doc.close()
    
    def map_images_to_questions(self) -> Dict[str, Any]:
        """
        Main function to map images to questions based on coordinates
        
        Returns:
            Dictionary containing mappings and statistics
        """
        logger.info("Starting coordinate-based image-question mapping")
        
        # Load extracted images data
        images_data = self._load_extracted_images()
        if not images_data:
            logger.error("No extracted images data found")
            return {"error": "No extracted images data found"}
        
        # Process each page
        all_mappings = []
        page_stats = {}
        
        # Group images by page
        images_by_page = {}
        for img in images_data.get('images', []):
            page = img['page']
            if page not in images_by_page:
                images_by_page[page] = []
            images_by_page[page].append(img)
        
        # Process each page with images
        for page_num, page_images in images_by_page.items():
            logger.info(f"Processing page {page_num} with {len(page_images)} images")
            
            # Extract questions from this page
            questions = self._extract_question_coordinates(page_num - 1)  # Convert to 0-based
            
            # Map images to questions
            page_mappings = self._match_images_to_questions(page_images, questions, page_num)
            all_mappings.extend(page_mappings)
            
            page_stats[page_num] = {
                'images': len(page_images),
                'questions': len(questions),
                'mappings': len(page_mappings)
            }
            
            logger.info(f"Page {page_num}: {len(questions)} questions, {len(page_images)} images, {len(page_mappings)} mappings")
        
        # Generate summary
        total_images = sum(stats['images'] for stats in page_stats.values())
        total_mappings = len(all_mappings)
        
        result = {
            'pdf_path': self.pdf_path,
            'mapping_method': 'coordinate_based',
            'total_images': total_images,
            'total_mappings': total_mappings,
            'mapping_success_rate': f"{(total_mappings/total_images)*100:.1f}%" if total_images > 0 else "0%",
            'page_statistics': page_stats,
            'mappings': all_mappings
        }
        
        logger.info(f"Mapping completed: {total_mappings}/{total_images} images mapped ({result['mapping_success_rate']})")
        return result
    
    def _load_extracted_images(self) -> Dict[str, Any]:
        """Load the extracted images JSON data"""
        try:
            with open(self.extracted_images_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Extracted images file not found: {self.extracted_images_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing extracted images JSON: {e}")
            return {}
    
    def _extract_question_coordinates(self, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract questions with their coordinates from a specific page
        
        Args:
            page_num: 0-based page number
            
        Returns:
            List of question dictionaries with coordinates
        """
        if not self.doc:
            return []
        
        page = self.doc[page_num]
        questions = []
        
        # Get text blocks with coordinates
        text_dict = page.get_text("dict")
        
        # Question patterns to look for
        question_patterns = [
            r'^Question\s+\d+',           # "Question 1", "Question 2"
            r'^\d+\.',                    # "1.", "2.", "3."
            r'^Practice\s+Example\s+\d+', # "Practice Example 1"
        ]
        
        combined_pattern = '|'.join(f'({pattern})' for pattern in question_patterns)
        
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                # Combine all text spans in this line
                line_text = ""
                line_bbox = None
                for span in line.get("spans", []):
                    line_text += span.get("text", "")
                    if line_bbox is None:
                        line_bbox = span.get("bbox")
                    else:
                        # Expand bbox to include this span
                        x0, y0, x1, y1 = line_bbox
                        sx0, sy0, sx1, sy1 = span.get("bbox", (x0, y0, x1, y1))
                        line_bbox = (min(x0, sx0), min(y0, sy0), max(x1, sx1), max(y1, sy1))
                line_text = line_text.strip()
                # Check if this line matches a question pattern
                if line_text and re.match(combined_pattern, line_text, re.IGNORECASE):
                    # Use the full matched string as question_number, just like TextExtractor
                    question_number = line_text
                    questions.append({
                        'question_text': line_text,
                        'question_number': question_number,
                        'page': page_num + 1,  # Convert back to 1-based
                        'y_coordinate': line_bbox[1] if line_bbox else 0,  # Top Y coordinate
                        'bbox': line_bbox,
                        'full_text': line_text
                    })
                    logger.debug(f"Found question on page {page_num + 1}: {question_number} at Y={line_bbox[1] if line_bbox else 0}")
        
        # Sort questions by Y coordinate (top to bottom)
        questions.sort(key=lambda q: q['y_coordinate'])
        
        return questions
    
    def _extract_question_number(self, text: str) -> str:
        """Extract question number from question text"""
        # Try different patterns
        patterns = [
            r'Question\s+(\d+)',
            r'^(\d+)\.',
            r'Practice\s+Example\s+(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "Unknown"
    
    def _match_images_to_questions(self, images: List[Dict], questions: List[Dict], page_num: int) -> List[Dict]:
        """
        Match images to questions on the same page
        
        Args:
            images: List of image dictionaries with coordinates
            questions: List of question dictionaries with coordinates
            page_num: Page number for reference
            
        Returns:
            List of mapping dictionaries
        """
        mappings = []
        
        for image in images:
            # Get image top Y coordinate
            image_y = image['coordinates']['y0']  # Top of image
            
            logger.debug(f"Processing image {image['filename']} at Y={image_y}")
            
            # Find questions above this image
            questions_above = [
                q for q in questions 
                if q['y_coordinate'] < image_y
            ]
            
            if questions_above:
                # Get the closest question (highest Y coordinate that's still above the image)
                closest_question = max(questions_above, key=lambda q: q['y_coordinate'])
                
                # Calculate distance
                distance = image_y - closest_question['y_coordinate']
                
                mapping = {
                    'image': {
                        'filename': image['filename'],
                        'filepath': image['filepath'],
                        'page': image['page'],
                        'coordinates': image['coordinates'],
                        'y_position': image_y
                    },
                    'question': {
                        'question_number': closest_question['question_number'],
                        'question_text': closest_question['question_text'],
                        'page': closest_question['page'],
                        'y_position': closest_question['y_coordinate']
                    },
                    'mapping_info': {
                        'method': 'coordinate_based',
                        'distance': distance,
                        'confidence': 'high' if distance < 200 else 'medium' if distance < 400 else 'low'
                    }
                }
                
                mappings.append(mapping)
                
                logger.info(f"Mapped {image['filename']} to Question {closest_question['question_number']} (distance: {distance:.1f})")
            
            else:
                # No question found above - this might be at the top of the page
                logger.warning(f"No question found above image {image['filename']} on page {page_num}")
                
                # Try to map to the first question on the page
                if questions:
                    first_question = min(questions, key=lambda q: q['y_coordinate'])
                    
                    mapping = {
                        'image': {
                            'filename': image['filename'],
                            'filepath': image['filepath'],
                            'page': image['page'],
                            'coordinates': image['coordinates'],
                            'y_position': image_y
                        },
                        'question': {
                            'question_number': first_question['question_number'],
                            'question_text': first_question['question_text'],
                            'page': first_question['page'],
                            'y_position': first_question['y_coordinate']
                        },
                        'mapping_info': {
                            'method': 'coordinate_based_fallback',
                            'distance': abs(image_y - first_question['y_coordinate']),
                            'confidence': 'low',
                            'note': 'Image above all questions - mapped to first question'
                        }
                    }
                    
                    mappings.append(mapping)
                    logger.info(f"Fallback mapping: {image['filename']} to first question {first_question['question_number']}")
        
        return mappings
    
    def save_mappings(self, mappings_data: Dict[str, Any], output_path: str = "output/image_question_mappings.json"):
        """Save the mappings to a JSON file"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(mappings_data, f, indent=2, default=str)
        
        logger.info(f"Mappings saved to {output_path}")
        return output_path


def extract_images_with_metadata(pdf_path, output_dir, output_json_path):
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    images = []
    img_count = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            img_count += 1
            filename = f"page{page_num+1}_img{img_index+1}.{image_ext}"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "wb") as img_file:
                img_file.write(image_bytes)

            # Get bbox and coordinates if available
            bbox = None
            coordinates = None
            # Try to get bbox from image blocks
            for block in page.get_text("dict")["blocks"]:
                if block["type"] == 1 and block.get("image"):
                    if block["image"] == xref:
                        bbox = block["bbox"]
                        x0, y0, x1, y1 = bbox
                        coordinates = {
                            "x0": x0,
                            "y0": y0,
                            "x1": x1,
                            "y1": y1,
                            "center_x": (x0 + x1) / 2,
                            "center_y": (y0 + y1) / 2
                        }
                        break

            # Fallback if bbox not found
            if bbox is None:
                bbox = [0, 0, base_image["width"], base_image["height"]]
                coordinates = {
                    "x0": 0,
                    "y0": 0,
                    "x1": base_image["width"],
                    "y1": base_image["height"],
                    "center_x": base_image["width"] / 2,
                    "center_y": base_image["height"] / 2
                }

            images.append({
                "page": page_num + 1,
                "index": img_index + 1,
                "filename": filename,
                "filepath": filepath,
                "width": base_image["width"],
                "height": base_image["height"],
                "bbox": bbox,
                "coordinates": coordinates
            })

    output = {
        "pdf_path": pdf_path,
        "output_directory": output_dir,
        "total_images": img_count,
        "images": images
    }

    with open(output_json_path, "w") as json_file:
        json.dump(output, json_file, indent=2)

    logger.info(f"Extracted {img_count} images to {output_dir}")

def map_images_to_questions_for_pdf(
    pdf_path,
    extracted_images_path,
    output_path
):
    """
    Maps images to questions for a specific PDF and saves the result.
    """
    with CoordinateImageMapper(pdf_path, extracted_images_path) as mapper:
        mappings = mapper.map_images_to_questions()
        mapper.save_mappings(mappings, output_path)
        logger.info(f"Image-question mappings saved to: {output_path}")
        return mappings
