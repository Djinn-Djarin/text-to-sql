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
    
    from src.agent_traccrop.tools.table_metadata import get_table_catalog_summary
    available_tables = get_table_catalog_summary(tuple(sorted(validator.allowed_tables)))
    
    system_prompt = f"""
You are a helpful agricultural assistant. You are assisting {user_name} (User ID: {user_id}).
The user has access to the Account ID: {account_id}

You have access to the following database tables:
{available_tables}

CRITICAL RULES FOR SQL QUERIES:
1. You are an autonomous agent. You MUST execute the `query_database` tool yourself.
2. NEVER GUESS COLUMNS OR VALUES! Use `describe_tables` to inspect columns, table business descriptions, linear parent/child relationships, and sample rows. (Use `get_schema_minimap` if you need to discover join paths across multiple tables).
3. Pay close attention to sample rows and valid column values provided in `describe_tables`.
4. NO CLARIFICATION DELAYS: When the user asks for "detailed information", "summary", or "details", DO NOT ask clarifying questions. Immediately write and execute the SQL query using `query_database` to fetch the data.
5. If a query with a string filter (e.g. WHERE status = '...') returns empty results `[]`, execute `SELECT DISTINCT column_name FROM ai_views.table` to discover valid DB values.
6. To ensure data security, you MUST query tables from the `ai_views` schema, not `public`. 
7. RESPONSE FORMATTING: When presenting database records, summarize both the primary scalar attributes (names, identifiers, key fields) AND any nested/JSON array data. Do not focus exclusively on nested JSON arrays at the expense of primary table fields.
8. ANTI-LOOP RULE: If a database query fails or returns empty results `[]` after 2 attempts, STOP TRYING and inform the user.
9. NEVER echo or repeat tool responses back to the user. Analyze tool output silently and proceed immediately to your next action or answer.
""".strip()

    # Truncate history to last 15 messages to prevent 413 Token Size errors on small models
    if len(messages) > 15:
        messages = messages[-15:]

    full_messages = [SystemMessage(content=system_prompt)] + messages
    # ====== CLEAN NON-REPEATING LOGGING ======
    thread_id = config.get("configurable", {}).get("thread_id", "default")
    import os
    os.makedirs("log", exist_ok=True)
    log_filename = f"log/{thread_id}.txt"
    file_exists = os.path.exists(log_filename) and os.path.getsize(log_filename) > 0

    with open(log_filename, "a", encoding="utf-8") as log_file:
        if not file_exists:
            log_file.write(f"[SYSTEM]: {system_prompt}\n\n")
        
        # Log ONLY the newest incoming message (Human input or Tool output)
        if messages:
            last_msg = messages[-1]
            log_file.write(f"[{last_msg.type.upper()}]: {last_msg.content}\n")
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                log_file.write(f"  Tool Calls: {last_msg.tool_calls}\n")
            log_file.write("\n")
        log_file.flush()
    # ==========================================

    response = llm_with_tools.invoke(full_messages)
    
    # [HOTFIX] Intercept Ollama's raw JSON output and convert to LangChain Tool Call
    if isinstance(response.content, str) and '"name"' in response.content and ('"arguments"' in response.content or '"args"' in response.content or '"parameters"' in response.content):
        import json
        import uuid
        import re
        try:
            # Find the first JSON object in the string using regex
            match = re.search(r'\{.*\}', response.content.strip(), re.DOTALL)
            if match:
                clean_json = match.group(0)
                parsed = json.loads(clean_json)
                if "name" in parsed:
                    args = parsed.get("arguments", parsed.get("args", parsed.get("parameters", {})))
                    response.tool_calls = [{
                        "name": parsed["name"],
                        "args": args,
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "tool_call"
                    }]
                    response.content = "" # Clear text so LangGraph executes the tool
        except Exception as e:
            pass
    
    # Log ONLY the AI's response (newest outgoing message)
    with open(log_filename, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{response.type.upper()}]: {response.content}\n")
        if hasattr(response, "tool_calls") and response.tool_calls:
            log_file.write(f"  Tool Calls: {response.tool_calls}\n")
        log_file.write("\n")
        log_file.flush()

    return {"messages": [response]}
