import pdfplumber
import re

class TableExtractor:
    def __init__(self):
        pass

    def extract_questions_from_table(self, pdf_path):
        """
        Extracts tables from the PDF and returns a list of dicts with keys:
        question_num, question_text, answer, mcq_options
        """
        questions = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        # Only process rows with 3 columns and a valid question number
                        if (
                            len(row) == 3
                            and row[0] is not None
                            and str(row[0]).strip().isdigit()
                        ):
                            question_num = str(row[0]).strip()
                            question_text = (row[1] or "").strip()
                            answer = (row[2] or "").strip()
                            
                            # Extract MCQ options from question_text
                            mcq_options = self._extract_mcq_options(question_text)
                            
                            questions.append({
                                "question_num": question_num,
                                "question_text": question_text,
                                "answer": answer,
                                "mcq_options": mcq_options
                            })
        return questions
    
    def _extract_mcq_options(self, text):
        """Simple MCQ option extraction"""
        options = []
        
        if not text:
            return options
        
        # Simple pattern: (a) text (b) text (c) text
        pattern = r'\(([a-e])\)\s*([^()]+?)(?=\([a-e]\)|$)'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        for match in matches:
            options.append({
                "letter": match[0].upper(),
                "text": match[1].strip()
            })
        
        return options
