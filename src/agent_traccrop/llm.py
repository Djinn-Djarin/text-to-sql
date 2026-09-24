from langchain_groq import ChatGroq
from src.agent_traccrop.config import GROQ_API_KEY

llm = ChatGroq(api_key=GROQ_API_KEY, model="openai/gpt-oss-120b", temperature=0)
