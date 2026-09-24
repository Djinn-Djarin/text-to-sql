from src.agent_traccrop.llm import llm
from src.agent_traccrop.db import vector_store
from langchain_core.messages import SystemMessage
from src.agent_traccrop.tools import execute_secure_sql
from src.agent_traccrop.tools import tools


# Bind the tools to the Groq model
llm_with_tools = llm.bind_tools(tools)

def call_model(state, config):
    """Invokes the LLM with the conversation history and user-specific context."""
    messages = state["messages"]

    system_prompt = (
        "You are a helpful agricultural assistant. "
        "If the user asks about their harvests or farm data, write a PostgreSQL query "
        "and use the 'query_database' tool to fetch the answer."
    )

    full_messages = [SystemMessage(content=system_prompt)] + messages

    response = llm_with_tools.invoke(full_messages)

    return {"messages": [response]}
