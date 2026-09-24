import getpass
import requests
import jwt
from src.agent_traccrop.config import AUTH_SERVER_URL
from src.agent_traccrop.graph import graph

def authenticate_user() -> str:
    """Handles login, fetches JWT, and returns the extracted user ID."""
    print("=== CropTrac Agent Login ===")
    import getpass

    # Add the default value to the prompt string so the user knows what it is
    email = input("Email [traccrops+Tsowner@gmail.com]: ") or "traccrops+Tsowner@gmail.com"

    password = getpass.getpass("Password [billTE$T1]: ") or "billTE$T1"
    
    # 1. Send credentials to your backend
    # Note: Adjust the endpoint ('/api/login') and payload structure to match your specific backend framework
    try:
        response = requests.post(
            f"{AUTH_SERVER_URL}/api/login",
            json={"email": email, "password": password},
            timeout=10
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"\nLogin failed: {e}")
        exit(1)
        
    auth_data = response.json()
    access_token = auth_data.get("success").get("access")
    
    if not access_token:
        print("\nLogin failed: No access token received.")
        exit(1)
        
    # 2. Decode the JWT to extract the identity
    # Since this is a client script reading its own token, we can bypass signature 
    # verification here (the backend will verify signatures when receiving requests).
    try:
        decoded_payload = jwt.decode(access_token, options={"verify_signature": False})
        
        # Adjust 'user_id' based on what your backend actually encodes in the JWT 
        # (it might be 'sub', 'grower_id', or 'id')
        user_id = str(decoded_payload.get("user_id")) 
        
        if not user_id or user_id == "None":
            raise ValueError("Token missing user_id field.")
            
        print("\nLogin successful!")
        return user_id
        
    except Exception as e:
        print(f"\nFailed to parse token identity: {e}")
        exit(1)


def main():
    # Run the authentication flow before starting the agent
    current_user_id = authenticate_user()
    print(f"Authenticated as User ID: {current_user_id}")
    
    # Configure LangGraph to isolate memory by this user ID
    config = {"configurable": {"thread_id": current_user_id}}
    
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