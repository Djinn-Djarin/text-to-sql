from functools import lru_cache
from typing import Optional
from langchain_core.messages import SystemMessage
from src.agent_traccrop.llm import llm
from src.agent_traccrop.tools.query_tools import tools
from src.agent_traccrop.tools.query_tools import validator

# Bind the tools to the Groq model
llm_with_tools = llm.bind_tools(tools)

def call_model(state, config):
    """Invoke the LLM with the conversation history and database context."""
    messages = state["messages"]

    # Extract user context from config
    user_id = config.get("configurable", {}).get("thread_id", "Unknown")
    user_name = config.get("configurable", {}).get("user_name", "User")
    account_id = config.get("configurable", {}).get("account_id")
    
    available_tables = ", ".join(validator.allowed_tables)
    
    system_prompt = f"""
You are a helpful agricultural assistant. You are assisting {user_name} (User ID: {user_id}).
The user has access to the Account ID: {account_id}

You have access to the following database tables:
{available_tables}

CRITICAL RULES FOR SQL QUERIES:
1. You do not know the exact columns for these tables. 
    - ALWAYS use `get_schema_minimap` first to see a high-level graph of how tables are related.
    - Then, ALWAYS use `describe_tables` to learn the exact columns of the specific 1-3 tables you want to query. DO NOT describe all tables at once to avoid token limits!
2. ONLY perform read-only SELECT queries.
3. To ensure data security, you MUST query tables from the `ai_views` schema, not `public` (e.g. `SELECT * FROM ai_views._01_user_management_employeeprofile`).
   The `ai_views` tables are already pre-filtered for the user's account, so you DO NOT need to add manual `WHERE account_id = ...` filters or join `accountmember` for security. Just query them naturally!
4. ANTI-LOOP RULE: If a database query returns empty results `[]` after 2 attempts, STOP TRYING. Simply inform the user that the data was not found or they do not have access to it. Do NOT keep retrying different variations.
""".strip()

    # Truncate history to last 15 messages to prevent 413 Token Size errors on small models
    if len(messages) > 15:
        messages = messages[-15:]

    full_messages = [SystemMessage(content=system_prompt)] + messages
    # ====== NEW LOGGING CODE ======
    thread_id = config.get("configurable", {}).get("thread_id", "default")
    import os
    os.makedirs("log", exist_ok=True)
    log_filename = f"log/{thread_id}.txt"
    with open(log_filename, "a", encoding="utf-8") as log_file:
        log_file.write("========== NEW LLM CALL ==========\n")
        for msg in full_messages:
            log_file.write(f"[{msg.type.upper()}]: {msg.content}\n")
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                log_file.write(f"  Tool Calls: {msg.tool_calls}\n")
        log_file.write("\n")
        log_file.flush()
    # ==============================
    response = llm_with_tools.invoke(full_messages)
    
    # Log the AI's response instantly
    with open(log_filename, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{response.type.upper()}]: {response.content}\n")
        if hasattr(response, "tool_calls") and response.tool_calls:
            log_file.write(f"  Tool Calls: {response.tool_calls}\n")
        log_file.write("\n")
        log_file.flush()

    return {"messages": [response]}
