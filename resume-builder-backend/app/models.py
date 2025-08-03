from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime
from .database import Base

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String)
    parsed_text = Column(String)
    llm_response = Column(String)
    upload_time = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
