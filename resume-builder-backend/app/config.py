import os
from dotenv import load_dotenv
import tempfile


load_dotenv()

TEMP_DIR = tempfile.gettempdir() 
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
UI_URL = os.getenv("UI_URL", "http://localhost:7777/")  # Default to local UI URL if not set