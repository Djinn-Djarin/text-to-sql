from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from src.agent_traccrop.tools.query_tools import tools
from src.agent_traccrop.state import AgentState
from src.agent_traccrop.nodes import call_model
from src.agent_traccrop.db import checkpointer

workflow = StateGraph(AgentState)

# 1. Add the main AI agent node
workflow.add_node("agent", call_model)

# 2. Add the Prebuilt ToolNode to automatically execute our SQL tool
tool_node = ToolNode(tools)
workflow.add_node("tools", tool_node)

# 3. Define the starting edge
workflow.add_edge(START, "agent")

# 4. Add Conditional Routing
# If the AI decides to call a tool, it routes to "tools".
# If the AI decides to just speak to the user, it routes to END.
workflow.add_conditional_edges("agent", tools_condition)

# 5. Loop back from the tools to the agent so it can read the database results
workflow.add_edge("tools", "agent")

# 6. Compile with the Postgres memory saver
graph = workflow.compile(checkpointer=checkpointer)