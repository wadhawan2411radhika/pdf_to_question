"""Simple LLM Vision Service for analyzing images."""

import os
import base64
import json
from typing import Dict, List, Any, Optional
import openai
from PIL import Image
import io


class VisionResult:
    """Simple result from vision analysis"""
    def __init__(self):
        self.question_text = None
        self.mcq_options = []
        self.mathematical_content = None
        self.has_diagram = False
        self.raw_response = ""


class LLMService:
    """Simple LLM Vision service"""
    
    def __init__(self):
        """Initialize with environment credentials"""
        self.api_base = os.getenv("LITELLM_API_URL")
        self.api_key = os.getenv("LITELLM_API_KEY")
        self.model = os.getenv("LITELLM_MODEL")

        self.client = openai.OpenAI(
            base_url=self.api_base,
            api_key=self.api_key
        )
        
        print(f"LLM SERVICE - Initialized")
    
    def analyze_image(self, image_path: str, analysis_type: str = "comprehensive") -> VisionResult:
        """Analyze image and return simple results"""
        try:
            # Convert image to base64
            image_base64 = self._encode_image(image_path)
            
            # Simple prompt
            prompt = """Analyze this image and extract:
1. Any question text
2. Multiple choice options (A, B, C, D, E)
3. Mathematical formulas
4. Whether it contains diagrams/figures

Return as JSON:
{
    "question_text": "...",
    "mcq_options": [{"letter": "A", "text": "..."}],
    "mathematical_content": "...",
    "has_diagram": true/false
}"""

            # Call LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                            }
                        ]
                    }
                ],
                max_tokens=800,
                temperature=0.1
            )
            
            # Parse response
            raw_response = response.choices[0].message.content
            result = self._parse_response(raw_response)
            
            print(f"LLM VISION - Analyzed {os.path.basename(image_path)}: question={bool(result.question_text)}, mcq={len(result.mcq_options)}")
            return result
            
        except Exception as e:
            print(f"LLM VISION ERROR - {e}")
            result = VisionResult()
            result.raw_response = f"Error: {str(e)}"
            return result
    
    def _encode_image(self, image_path: str) -> str:
        """Convert image to base64"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large
                max_size = 1024
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Convert to base64
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                return base64.b64encode(buffer.getvalue()).decode('utf-8')
                
        except Exception as e:
            print(f"Error encoding image: {e}")
            raise
    
    def _parse_response(self, response: str) -> VisionResult:
        """Parse LLM response"""
        result = VisionResult()
        result.raw_response = response
        
        try:
            # Try JSON parsing first
            if '{' in response:
                # Extract JSON part
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                data = json.loads(json_str)
                
                result.question_text = data.get('question_text')
                result.mcq_options = data.get('mcq_options', [])
                result.mathematical_content = data.get('mathematical_content')
                result.has_diagram = data.get('has_diagram', False)
            else:
                # Simple text parsing fallback
                result = self._parse_text_response(response)
                
        except json.JSONDecodeError:
            # Fallback to text parsing
            result = self._parse_text_response(response)
        
        return result
    
    def _parse_text_response(self, response: str) -> VisionResult:
        """Simple text parsing fallback"""
        result = VisionResult()
        result.raw_response = response
        
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Look for question text
            if any(word in line.lower() for word in ['question:', 'q:', 'problem:']):
                result.question_text = line
            
            # Look for MCQ options
            if line.startswith(('A:', 'B:', 'C:', 'D:', 'E:')):
                letter = line[0]
                text = line[2:].strip()
                result.mcq_options.append({"letter": letter, "text": text})
            
            # Look for math content
            if any(symbol in line for symbol in ['=', '+', '-', '×', '÷', '∑', '∫']):
                result.mathematical_content = line
            
            # Look for diagrams
            if any(word in line.lower() for word in ['diagram', 'chart', 'graph', 'figure']):
                result.has_diagram = True
        
        return result
