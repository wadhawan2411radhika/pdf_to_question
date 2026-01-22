# PDF Question Extractor

A robust PDF processing pipeline that extracts **questions** from academic PDFs as structured JSON. Handles **LaTeX**, **inline/figure images**, **multiple-choice options**, **multi-part sub-questions**, and **tables** with coordinate-based asset linking.

## Features

- **Dual Processing Strategy**: Automatically detects PDF type (text-heavy vs table-dominant) and applies appropriate extraction method
- **Question Structure Support**: Handles main questions, subparts (a., (i), etc.), and MCQ options (A:, B:, C:, etc.)
- **Asset Extraction**: Extracts and links images and tables with coordinate-based mapping
- **LaTeX Support**: Detects and renders mathematical expressions
- **Parallel Processing**: Supports ≥5 PDFs concurrently without crashes
- **Fast Performance**: Processes PDFs ≤3 minutes for 10-page documents
- **Robust Schema**: Custom JSON schema with proper asset referencing

## Quick Start

### Prerequisites

- Python 3.10+
- Virtual environment (recommended)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/wadhawan2411radhika/pdf_to_question.git
cd pdf_to_ingestion
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (optional):
```bash
# LLM API credentials for enhanced vision analysis (optional)
export OPENAI_API_KEY="your-api-key"
```

### Running the API

Start the FastAPI server:
```bash
python -m src.main
```

The API will be available at `http://localhost:8000`

### API Usage

Extract questions from a PDF:
```bash
curl -X POST "http://localhost:8000/extract" \
     -H "Content-Type: application/json" \
     -d '{"pdf_path": "/path/to/your/document.pdf"}'
```

Response:
```json
{
  "status": "ok",
  "output_json_path": "/path/to/output.json",
  "assets_dir": "/path/to/assets/"
}
```

### Batch Processing

Process multiple PDFs using the evaluation script:
```bash
bash run_eval.sh data/dev/*.pdf output/
```

This script processes all PDFs concurrently and reports:
- Per-PDF processing times
- Success/failure rates
- Validation errors

## Output Schema

The system generates structured JSON conforming to our custom schema defined in `src/state.py`:

### Document Structure
```json
{
  "document_metadata": {
    "pdf_name": "example.pdf",
    "pdf_path": "/path/to/example.pdf",
    "total_pages": 10,
    "processing_timestamp": "2024-01-01T12:00:00Z",
    "processing_time_seconds": 45.2,
    "dominance_type": "text-dominant",
    "extraction_method": "TextExtractor"
  },
  "questions": [...],
  "extraction_stats": {
    "total_questions": 15,
    "mcq_count": 5,
    "subpart_count": 8,
    "images_extracted": 3,
    "tables_extracted": 2,
    "processing_errors": []
  }
}
```

### Question Structure
```json
{
  "question_number": "1.",
  "question_type": "evaluate",
  "question_text": "Calculate the sum of the series...",
  "question_latex": "\\sum_{n=1}^{\\infty} \\frac{1}{n^2}",
  "pdf_page": 1,
  "subpart_flag": true,
  "mcq_flag": false,
  "subparts": [
    {
      "subpart_number": "a.",
      "subpart_text": "Find the first 5 terms",
      "subpart_latex": null,
      "question_type": "evaluate",
      "assets": [],
      "mcq_options": []
    }
  ],
  "mcq_options": [],
  "assets": [
    {
      "asset_type": "image",
      "asset_path": "assets/page1_image1.png",
      "asset_description": "Graph showing convergence",
      "bbox": {"x0": 100, "y0": 200, "x1": 400, "y1": 300},
      "page_number": 1
    }
  ]
}
```

## Architecture

### Core Components

- **Orchestrator**: Main processing coordinator that determines PDF type and routes to appropriate extractor
- **TextExtractor**: Handles text-heavy PDFs with regex-based question parsing
- **TableVisionExtractor**: Processes table-dominant PDFs with LLM vision analysis
- **CoordinateImageMapper**: Maps images to questions using spatial coordinates
- **CoordinateTableMapper**: Links tables to questions based on proximity
- **LLMService**: Optional vision analysis for enhanced image understanding
- **OutputManager**: Manages file organization and asset storage

### Processing Pipeline

1. **PDF Analysis**: Determine table density to classify as text-dominant or table-dominant
2. **Content Extraction**: Apply appropriate extraction strategy based on PDF type
3. **Question Parsing**: Extract questions using pattern matching (1., Question 1, Practice Example 1)
4. **Subpart Detection**: Handle nested structures (a., (i), Q1(a)(i))
5. **Asset Linking**: Map images and tables to questions using coordinate analysis
6. **Enhancement**: Optional LLM vision analysis for image content understanding
7. **Output Generation**: Save structured JSON with referenced asset files

## Development

### Running Tests

```bash
# Process development set
bash run_eval.sh data/dev/*.pdf test_output/
```

### Project Structure

```
src/
├── main.py                    # FastAPI application entry point
├── orchestrator.py            # Main processing coordinator
├── state.py                   # Data models and JSON schema
├── config.py                  # Configuration and logging
├── output_manager.py          # File organization and asset management
├── llm_service.py            # LLM vision analysis service
├── text_pipeline/
│   ├── text_extractor.py     # Text-focused PDF processing
│   ├── coordinate_image_mapper.py  # Image-question mapping
│   ├── coordinate_table_mapper.py  # Table-question mapping
│   └── latex_utils.py        # LaTeX detection and rendering
└── table_pipeline/
    ├── table_vision_extractor.py   # Table-focused processing
    ├── image_table_mapper.py       # Image-table coordinate mapping
    ├── image_tablecell_mapper.py   # Cell-level image mapping
    └── table_text_extractor.py     # Table text extraction
```

## Performance & Constraints

### Runtime Performance
- **Target**: ≤3 minutes per 10-page PDF
- **Measurement**: Automated timing with statistical analysis
- **Monitoring**: Per-PDF processing times logged

### Parallelism Support
- **Target**: ≥5 PDFs processed concurrently
- **Implementation**: ThreadPoolExecutor with configurable worker count
- **Graceful Degradation**: Error logging without system crashes

### Robustness Features
- **MCQ Options**: Accurately captures A:, B:, C: format with varying layouts
- **Multi-part Numbering**: Preserves hierarchy (Q1(a)(i), Q1(a)(ii))
- **Table Structures**: Maintains row/column relationships
- **Figure References**: Links images to questions with bounding box coordinates

## Evaluation

The system includes comprehensive evaluation framework:

- **Automated Testing**: `run_eval.sh` processes multiple PDFs with performance metrics
- **Manual Validation**: Ground truth comparison for accuracy assessment
- **Error Analysis**: Systematic categorization of extraction failures
- **Statistical Rigor**: Confidence intervals and significance testing

See `EVAL.md` for detailed evaluation methodology and `NOTES.md` for development approach.

## Limitations

- **Question Detection**: Relies on consistent numbering patterns - struggles with irregular formats
- **Image Mapping**: Works best with structured layouts - may mislink in complex multi-column documents
- **LaTeX Support**: Basic symbol replacement only - doesn't handle complex mathematical expressions
- **Table Parsing**: Sequential linking may not capture semantic relationships

## Next Steps

1. **ML-based Question Detection**: Improve boundary detection for irregular formats
2. **Enhanced LaTeX Processing**: Integrate proper LaTeX parser for mathematical content
3. **Semantic Table Linking**: Use content analysis for better table-question relationships
4. **Multi-column Support**: Better handling of complex page layouts

## License

MIT License
