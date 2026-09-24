import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL_DEV")
AUTH_SERVER_URL = os.getenv("AUTH_SERVER_URL") 


if not all([GROQ_API_KEY, DATABASE_URL, AUTH_SERVER_URL]):
    raise ValueError("Missing required environment variables in .env")
