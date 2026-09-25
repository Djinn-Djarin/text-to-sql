import os
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool
from langchain_postgres import PGVector 
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_huggingface import HuggingFaceEmbeddings

from src.agent_traccrop.config import DATABASE_URL

load_dotenv()
# 1. LangGraph Memory Pool 
pool = ConnectionPool(
    conninfo=DATABASE_URL,
    max_size=20,
    kwargs={"autocommit": True}
)

checkpointer = PostgresSaver(pool)
checkpointer.setup() 

# 2. Vector Store Setup
cache_folder = os.getenv("HF_HOME")
local_files_only = os.getenv("HF_LOCAL_FILES_ONLY", "false").strip().lower() in {
    "1",
    "true",
    "yes",
}
embedding_kwargs = {"local_files_only": True} if local_files_only else {}
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    cache_folder=cache_folder,
    model_kwargs=embedding_kwargs,
    show_progress=False,
)


# FIX: LangChain Postgres requires the sqlalchemy psycopg driver format
# This converts "postgresql://..." to "postgresql+psycopg://..."
vector_db_url = DATABASE_URL
if vector_db_url.startswith("postgresql://"):
    vector_db_url = vector_db_url.replace("postgresql://", "postgresql+psycopg://")
elif vector_db_url.startswith("postgres://"):
    vector_db_url = vector_db_url.replace("postgres://", "postgresql+psycopg://")

# FIX: Initialize PGVector using the formatted connection string
vector_store = PGVector(
    embeddings=embeddings,
    collection_name="traccrop_docs",
    connection=vector_db_url,
    use_jsonb=True, 
)

vector_store.create_tables_if_not_exists()