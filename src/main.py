"""Question Extractor FastAPI Application."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from orchestrator import Orchestrator
from config import setup_logging

# Setup centralized logging
logger = setup_logging()
logger.info("=== PDF Ingestion API Starting ===")

app = FastAPI(title="PDF Ingestion API")

class PDFRequest(BaseModel):
    pdf_path: str

class PDFResponse(BaseModel):
    status: str
    output_json_path: str
    assets_dir: str

@app.post("/extract", response_model=PDFResponse)
async def extract_pdf(request: PDFRequest):
    """Extract content from PDF."""
    import time
    
    start_time = time.time()
    
    if not os.path.exists(request.pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    logger.info(f"Starting PDF extraction for: {request.pdf_path}")
    
    orchestrator = Orchestrator()
    response = orchestrator.process_pdf(request.pdf_path)
    
    processing_time = time.time() - start_time
    logger.info(f"✅ PDF extraction completed in {processing_time:.2f} seconds")
    logger.info(f"📄 Output JSON: {response['output_json_path']}")
    logger.info(f"📁 Assets directory: {response['assets_dir']}")
    
    return PDFResponse(
        status="ok",
        output_json_path=response["output_json_path"],
        assets_dir=response["assets_dir"]
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
