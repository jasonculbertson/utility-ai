from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pge_bill_analyzer import PGEBillAnalyzer
import tempfile
import os
import uvicorn
from typing import Optional
import json

app = FastAPI(title="PG&E Bill Analyzer")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/analyze-bill")
async def analyze_bill(
    file: UploadFile = File(...),
    source: Optional[str] = None
):
    """
    Analyze a PG&E bill PDF
    
    Args:
        file: PDF file to analyze
        source: Optional source identifier (e.g., 'email', 'web_upload')
    
    Returns:
        Analysis results including extracted data and storage info
    """
    # Verify file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Process the bill
        analyzer = PGEBillAnalyzer()
        result = await analyzer.process_bill(temp_path)
        
        # Clean up
        os.unlink(temp_path)
        
        return result
        
    except Exception as e:
        # Clean up on error
        if 'temp_path' in locals():
            os.unlink(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
