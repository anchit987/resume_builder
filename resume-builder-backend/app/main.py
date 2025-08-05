from fastapi.responses import FileResponse, JSONResponse
import os
import json
import re
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Depends,
    Request,
    Form,
    BackgroundTasks,
)
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from app import models, database, schemas
from app.utils import file_parser, virus_scan, llm_handler, cleanup, pdf_generator
from app.config import TEMP_DIR

app = FastAPI()

# CORS setup
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://your-production-frontend.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=database.engine)


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/upload")
async def upload_resume(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_input: str = Form(None),
    db: Session = Depends(get_db)
):
    print("[UPLOAD] Received file:", file.filename)
    ext = os.path.splitext(file.filename)[1]
    print("[UPLOAD] File extension:", ext)

    if ext not in [".pdf", ".docx"]:
        print("[UPLOAD] Unsupported file type")
        return JSONResponse({"error": "Unsupported file type"}, status_code=400)

    temp_path = os.path.join(TEMP_DIR, file.filename)
    print("[UPLOAD] Saving temp file at:", temp_path)
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    print("[UPLOAD] Parsing file...")
    text = file_parser.parse_pdf(temp_path) if ext == ".pdf" else file_parser.parse_docx(temp_path)

    print("[UPLOAD] Calling LLM...")
    llm_response = llm_handler.call_llm_with_resume(text, user_input)
    print("[UPLOAD] LLM response (raw):", llm_response)

    print("[UPLOAD] Cleaning LLM response")
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", llm_response, re.DOTALL)
    if match:
        llm_response = match.group(1)
        print("[UPLOAD] Cleaned LLM JSON extracted")
    else:
        print("[UPLOAD] No markdown wrapping detected, assuming valid JSON")

    ip = request.client.host
    print("[UPLOAD] Client IP:", ip)

    resume = models.Resume(
        original_filename=file.filename,
        parsed_text=text,
        llm_response=llm_response,
        ip_address=ip
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    print("[UPLOAD] Resume stored in DB with ID:", resume.id)

    cleanup.cleanup_file(temp_path)
    print("[UPLOAD] Temp file cleaned up.")

    try:
        parsed_json = json.loads(llm_response)
    except Exception as e:
        print("[UPLOAD] JSON parsing failed:", e)
        print("[UPLOAD] Invalid JSON content:", llm_response)
        return JSONResponse({"error": "Invalid response from language model"}, status_code=500)

    print("[UPLOAD] Parsed JSON keys:", parsed_json.keys())

    resume_data = {
        "name": parsed_json.get("name", ""),
        "email": parsed_json.get("email", ""),
        "phone": parsed_json.get("phone", ""),
        "location": parsed_json.get("location", ""),
        "linkedin": parsed_json.get("linkedin", ""),
        "github": parsed_json.get("github", ""),
        "portfolio": parsed_json.get("portfolio", ""),
        "summary": parsed_json.get("summary", ""),
        "skills": parsed_json.get("skills", []),
        "experience": parsed_json.get("experience", []),
        "education": parsed_json.get("education", []),
        "projects": parsed_json.get("projects", []),
        "certifications": parsed_json.get("certifications", []),
    }

    print("[UPLOAD] Resume data prepared for PDF rendering")

    pdf_path, log_output = pdf_generator.render_resume_to_pdf(resume_data, TEMP_DIR, return_log=True)

    print("[UPLOAD] PDF path returned:", pdf_path, type(pdf_path))

    # Check if PDF generation failed
    if not pdf_path or not os.path.exists(pdf_path):
        print("[UPLOAD] ERROR - PDF generation failed")
        print("[UPLOAD] pdflatex output:\n", log_output)
        return JSONResponse({"error": "PDF generation failed", "log": log_output}, status_code=500)

    # Schedule cleanup for later
    background_tasks.add_task(cleanup.cleanup_file, pdf_path)

    print("[UPLOAD] Returning FileResponse")
    return FileResponse(
        path=pdf_path,
        filename="resume.pdf",
        media_type="application/pdf"
    )
