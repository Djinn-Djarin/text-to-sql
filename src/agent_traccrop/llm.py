from langchain_groq import ChatGroq
from src.agent_traccrop.config import GROQ_API_KEY

llm = ChatGroq(api_key=GROQ_API_KEY, model="meta-llama/llama-prompt-guard-2-86m", temperature=0)
