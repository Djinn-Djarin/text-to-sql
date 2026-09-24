from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # add_messages ensures new messages are appended, not overwritten
    messages: Annotated[list, add_messages]

    # You can add specific state variables here later if needed
    # e.g., user_role: str
