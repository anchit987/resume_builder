from pydantic import BaseModel
from datetime import datetime

class ResumeCreate(BaseModel):
    original_filename: str
    parsed_text: str
    llm_response: str
    ip_address: str

class ResumeOut(ResumeCreate):
    upload_time: datetime
