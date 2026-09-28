
import argparse
import uuid
from src.agent_traccrop.graph import graph
from src.agent_traccrop.auth import AuthManager
from src.agent_traccrop.config import AUTH_SERVER_URL


def main():
    parser = argparse.ArgumentParser(description="CropTrac AI Agent CLI")
    parser.add_argument("-s", "--session", type=str, help="Session / Thread ID to resume existing conversation")
    args = parser.parse_args()

    auth = AuthManager()
    # Run the authentication flow before starting the agent
    current_user_id = auth.login()
    auth.load_user_info()
    print(f"Authenticated as User ID: {current_user_id}")
    
    session_id = args.session if args.session else str(uuid.uuid4())
    print(f"Active Session ID: {session_id}")
    
    # Configure LangGraph to isolate memory by this user ID
    config = {"configurable": {"thread_id": session_id,
                                "user_id": current_user_id,
                                "user_name": auth.user_name,
                                "account_id": auth.account_id},
              "recursion_limit": 30}
    
    print("\nStarting Agent. Type 'quit' to exit.")
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            break
            
        print("Agent is thinking...")
        
        from langgraph.errors import GraphRecursionError
        try:
            events = graph.stream(
                {"messages": [("user", user_input)]},
                config=config,
                stream_mode="values"
            )
            
            printed_messages = set()
            for event in events:
                last_msg = event["messages"][-1]
                if last_msg.type == "ai" and last_msg.content:
                    msg_id = getattr(last_msg, "id", str(hash(last_msg.content)))
                    if msg_id not in printed_messages:
                        printed_messages.add(msg_id)
                        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                            print(f"\n🤔 [Thinking/Planning]: {last_msg.content}")
                        else:
                            print(f"\n🤖 Agent:\n{last_msg.content}")
        except GraphRecursionError:
            print("\n⚠️ Agent hit the step limit while self-correcting. Please try asking your question again!")

if __name__ == "__main__":
    main()