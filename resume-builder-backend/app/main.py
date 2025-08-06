from fastapi.responses import FileResponse, JSONResponse
import os
import json
import re
import logging
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Depends,
    Request,
    Form,
    BackgroundTasks,
    HTTPException
)
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from app import models, database, schemas
from app.utils import cleanup
from app.config import TEMP_DIR

# Import enhanced utilities
from app.utils import file_parser  # Use your original parser
from app.utils.llm_handler import EnhancedLLMHandler
from app.utils.pdf_generator import EnhancedPDFGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Enhanced Resume Builder API",
    description="AI-powered resume processing with improved text extraction and ATS optimization",
    version="2.0.0"
)

# CORS setup
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "https://your-production-frontend.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize enhanced components
llm_handler = EnhancedLLMHandler()
pdf_generator = EnhancedPDFGenerator()

# Create database tables
models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}

@app.get("/system-check")
async def system_check():
    """Check system requirements and dependencies."""
    checks = {}
    
    # Check LaTeX installation
    latex_ok, latex_msg = pdf_generator.check_latex_installation()
    checks["latex"] = {"status": "ok" if latex_ok else "error", "message": latex_msg}
    
    # Check temp directory
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
        checks["temp_dir"] = {"status": "ok", "path": TEMP_DIR}
    except Exception as e:
        checks["temp_dir"] = {"status": "error", "message": str(e)}
    
    # Check database connection
    try:
        db = next(get_db())
        db.execute("SELECT 1")
        checks["database"] = {"status": "ok"}
        db.close()
    except Exception as e:
        checks["database"] = {"status": "error", "message": str(e)}
    
    overall_status = "ok" if all(check["status"] == "ok" for check in checks.values()) else "error"
    
    return {
        "overall_status": overall_status,
        "checks": checks
    }

@app.post("/api/upload")
async def upload_resume(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_input: str = Form(None),
    target_role: str = Form(...),
    db: Session = Depends(get_db)
):
    """Enhanced resume upload and processing endpoint."""
    
    logger.info(f"[UPLOAD] Processing file: {file.filename}")
    
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        ext = os.path.splitext(file.filename)[1].lower()
        logger.info(f"[UPLOAD] File extension: {ext}")
        
        if ext not in [".pdf", ".docx"]:
            logger.warning(f"[UPLOAD] Unsupported file type: {ext}")
            return JSONResponse(
                {"error": "Unsupported file type. Please upload PDF or DOCX files only."}, 
                status_code=400
            )
        
        # Create temp file path with unique name to avoid conflicts
        import uuid
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        temp_path = os.path.join(TEMP_DIR, unique_filename)
        
        # Ensure temp directory exists
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        # Save uploaded file
        logger.info(f"[UPLOAD] Saving temp file: {temp_path}")
        with open(temp_path, "wb") as f:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Empty file uploaded")
            f.write(content)
        
        # Parse file with enhanced parser
        logger.info("[UPLOAD] Parsing file with enhanced parser...")
        try:
            # With this:
            if ext == ".pdf":
                text = file_parser.parse_pdf(temp_path)
            else:
                text = file_parser.parse_docx(temp_path)
            
            if not text or len(text.strip()) < 50:
                logger.warning("[UPLOAD] Very little text extracted from file")
                cleanup.cleanup_file(temp_path)
                return JSONResponse(
                    {
                        "error": "Unable to extract sufficient text from the file. Please ensure the file is not corrupted or image-based.",
                        "extraction_info": "Very little text extracted from the file"}, 
                    status_code=400
                )
                
        except Exception as e:
            logger.error(f"[UPLOAD] File parsing failed: {str(e)}")
            cleanup.cleanup_file(temp_path)
            return JSONResponse(
                {"error": f"File parsing failed: {str(e)}"}, 
                status_code=500
            )
        
        # Process with enhanced LLM handler
        logger.info("[UPLOAD] Processing with enhanced LLM...")
        try:
            llm_response = llm_handler.call_llm_with_resume(text, user_input or "", target_role)
            logger.info("[UPLOAD] LLM processing completed successfully")
            
        except Exception as e:
            logger.error(f"[UPLOAD] LLM processing failed: {str(e)}")
            cleanup.cleanup_file(temp_path)
            return JSONResponse(
                {"error": f"AI processing failed: {str(e)}"}, 
                status_code=500
            )
        
        # Store in database (optional - you mentioned no storage needed)
        try:
            ip = request.client.host
            resume = models.Resume(
                original_filename=file.filename,
                parsed_text=text[:5000],  # Truncate for storage
                llm_response=llm_response[:10000],  # Truncate for storage
                ip_address=ip
            )
            db.add(resume)
            db.commit()
            logger.info(f"[UPLOAD] Resume logged in DB with ID: {resume.id}")
        except Exception as e:
            logger.warning(f"[UPLOAD] Database logging failed (continuing): {str(e)}")
        
        # Clean up temp file
        cleanup.cleanup_file(temp_path)
        
        # Parse JSON response
        try:
            parsed_json = json.loads(llm_response)
            logger.info(f"[UPLOAD] Successfully parsed JSON with keys: {list(parsed_json.keys())}")
            logger.info(f"[UPLOAD] Full JSON response: {parsed_json}")
        except json.JSONDecodeError as e:
            logger.error(f"[UPLOAD] JSON parsing failed: {str(e)}")
            return JSONResponse(
                {
                    "error": "Invalid response format from AI processing", 
                    "raw_response": llm_response[:500]
                }, 
                status_code=500
            )
        
        # Generate PDF with enhanced generator
        logger.info("[UPLOAD] Generating PDF with enhanced generator...")
        try:
            pdf_path, log_output = pdf_generator.render_resume_to_pdf(
                parsed_json, 
                TEMP_DIR, 
                return_log=True
            )
            
            if not pdf_path or not os.path.exists(pdf_path):
                logger.error("[UPLOAD] PDF generation failed")
                return JSONResponse(
                    {
                        "error": "PDF generation failed", 
                        "latex_log": log_output,
                        "data_received": list(parsed_json.keys())
                    }, 
                    status_code=500
                )
            
            logger.info(f"[UPLOAD] PDF generated successfully: {pdf_path}")
            
        except Exception as e:
            logger.error(f"[UPLOAD] PDF generation exception: {str(e)}")
            return JSONResponse(
                {"error": f"PDF generation failed: {str(e)}"}, 
                status_code=500
            )
        
        # Schedule cleanup
        background_tasks.add_task(cleanup.cleanup_file, pdf_path)
        
        # Return PDF file
        logger.info("[UPLOAD] Returning PDF file")
        return FileResponse(
            path=pdf_path,
            filename=f"resume_{file.filename.split('.')[0]}.pdf",
            media_type="application/pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[UPLOAD] Unexpected error: {str(e)}")
        return JSONResponse(
            {"error": f"An unexpected error occurred: {str(e)}"}, 
            status_code=500
        )

@app.post("/preview")
async def preview_resume_data(
    request: Request,
    file: UploadFile = File(...),
    user_input: str = Form(None)
):
    """Preview extracted resume data without generating PDF."""
    
    logger.info(f"[PREVIEW] Processing file: {file.filename}")
    
    try:
        # Validate and parse file (similar to upload but return JSON data)
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in [".pdf", ".docx"]:
            return JSONResponse(
                {"error": "Unsupported file type"}, 
                status_code=400
            )
        
        # Save and parse file
        import uuid
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        temp_path = os.path.join(TEMP_DIR, unique_filename)
        
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        with open(temp_path, "wb") as f:
            f.write(await file.read())
        
        # Parse with enhanced parser
        if ext == ".pdf":
            text, extraction_info = file_parser.parse_pdf(temp_path)
        else:
            text, extraction_info = file_parser.parse_docx(temp_path)
        
        # Process with LLM
        llm_response = llm_handler.call_llm_with_resume(text, user_input or "")
        
        # Clean up
        cleanup.cleanup_file(temp_path)
        
        # Return structured data
        parsed_json = json.loads(llm_response)
        
        return JSONResponse({
            "status": "success",
            "extraction_info": extraction_info,
            "resume_data": parsed_json
        })
        
    except Exception as e:
        logger.error(f"[PREVIEW] Error: {str(e)}")
        return JSONResponse(
            {"error": f"Preview generation failed: {str(e)}"}, 
            status_code=500
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777) 