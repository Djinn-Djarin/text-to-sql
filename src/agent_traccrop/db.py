import os
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

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