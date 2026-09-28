import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL") 
DATABASE_URL = os.getenv("DATABASE_URL_DEV")
AUTH_SERVER_URL = os.getenv("AUTH_SERVER_URL") 


if not all([OLLAMA_URL, DATABASE_URL, AUTH_SERVER_URL]):
    raise ValueError("Missing required environment variables in .env")
