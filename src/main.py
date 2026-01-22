"""Question Extractor FastAPI Applicationls - Minimal API."""

import sys
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from orchestrator import Orchestrator
from config import setup_logging, Config

# Setup centralized logging
logger = setup_logging()
logger.info("=== PDF Ingestion API Starting ===")

# Thread pool for parallel processing
config = Config()
executor = ThreadPoolExecutor(max_workers=config.MAX_PARALLEL_PDFS)

app = FastAPI(title="PDF Ingestion API")

class PDFRequest(BaseModel):
    pdf_path: str
    output_dir: str = "output"  # Optional output directory, defaults to "output"

class PDFResponse(BaseModel):
    status: str
    output_json_path: str
    assets_dir: str

def process_pdf_sync(pdf_path: str, output_dir: str = "output"):
    """Process PDF synchronously."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    orchestrator = Orchestrator()
    return orchestrator.process_pdf(pdf_path, output_dir=output_dir)

@app.post("/extract", response_model=PDFResponse)
async def extract_pdf(request: PDFRequest):
    """Extract content from PDF."""
    logger.info(f"Starting PDF extraction for: {request.pdf_path}")
    
    try:
        # Run in thread pool to enable parallelism
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, process_pdf_sync, request.pdf_path, request.output_dir)
        
        logger.info(f"PDF extraction completed: {result['output_json_path']}")
        
        return PDFResponse(
            status="ok",
            output_json_path=result["output_json_path"],
            assets_dir=result["assets_dir"]
        )
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        logger.error(f"Permission denied: {str(e)}")
        raise HTTPException(status_code=403, detail=f"Permission denied: {str(e)}")
    except ValueError as e:
        logger.error(f"PDF processing error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"PDF processing failed: {str(e)}")
    except ConnectionError as e:
        logger.error(f"LLM service connection error: {str(e)}")
        raise HTTPException(status_code=503, detail=f"LLM service unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Processing error: {str(e)}", exc_info=True)
        error_msg = str(e).lower()
        
        # Check for PDF-related errors
        if any(keyword in error_msg for keyword in ['pdf', 'root object', 'invalid pdf', 'corrupted']):
            raise HTTPException(status_code=422, detail=f"Invalid PDF file: {str(e)}")
        # Check for permission errors
        elif any(keyword in error_msg for keyword in ['permission', 'read-only', 'errno 13', 'errno 30']):
            raise HTTPException(status_code=403, detail=f"Permission denied: {str(e)}")
        # Check for LLM service errors
        elif any(keyword in error_msg for keyword in ['openai', 'api', 'connection', 'timeout']):
            raise HTTPException(status_code=503, detail=f"LLM service error: {str(e)}")
        else:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
