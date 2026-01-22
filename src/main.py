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

class PDFResponse(BaseModel):
    status: str
    output_json_path: str
    assets_dir: str

def process_pdf_sync(pdf_path: str):
    """Process PDF synchronously."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    orchestrator = Orchestrator()
    return orchestrator.process_pdf(pdf_path)

@app.post("/extract", response_model=PDFResponse)
async def extract_pdf(request: PDFRequest):
    """Extract content from PDF."""
    logger.info(f"Starting PDF extraction for: {request.pdf_path}")
    
    try:
        # Run in thread pool to enable parallelism
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, process_pdf_sync, request.pdf_path)
        
        logger.info(f"PDF extraction completed: {result['output_json_path']}")
        
        return PDFResponse(
            status="ok",
            output_json_path=result["output_json_path"],
            assets_dir=result["assets_dir"]
        )
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
