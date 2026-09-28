import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# Use ChatOpenAI pointing to Ollama's OpenAI-compatible endpoint.
# This ensures that tool calling schemas are passed flawlessly to Qwen!
llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME"),
    base_url=f'{os.getenv("OLLAMA_URL", "https://little-drinks-smell.loca.lt").rstrip("/")}/v1',
    api_key="ollama", # Placeholder, required by the client
    temperature=0,
    default_headers={
        "bypass-tunnel-reminder": "true"
    }
)