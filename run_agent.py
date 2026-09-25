
import uuid
from src.agent_traccrop.graph import graph
from src.agent_traccrop.auth import AuthManager
from src.agent_traccrop.config import AUTH_SERVER_URL


def main():
    auth = AuthManager()
    # Run the authentication flow before starting the agent
    current_user_id = auth.login()
    auth.load_user_info()
    print(f"Authenticated as User ID: {current_user_id}")
    session_id = str(uuid.uuid4())
    # Configure LangGraph to isolate memory by this user ID
    config = {"configurable": {"thread_id": session_id,
                                "user_id": current_user_id,
                                "user_name": auth.user_name,
                                "account_id": auth.account_id},
              "recursion_limit": 15}
    
    print("\nStarting Agent. Type 'quit' to exit.")
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            break
            
        print("Agent is thinking...")
        
        events = graph.stream(
            {"messages": [("user", user_input)]},
            config=config,
            stream_mode="values"
        )
        
        for event in events:
            if event["messages"][-1].type == "ai":
                # Ensure we don't print empty tool-call messages
                if event['messages'][-1].content:
                    print(f"\nAgent: {event['messages'][-1].content}")

if __name__ == "__main__":
    main()