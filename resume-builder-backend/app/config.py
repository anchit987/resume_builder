import os
from dotenv import load_dotenv
import tempfile


load_dotenv()

TEMP_DIR = tempfile.gettempdir() 
LLM_API_KEY = os.getenv("LLM_API_KEY", "")