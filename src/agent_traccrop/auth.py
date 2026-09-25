import getpass
import requests
import jwt
from typing import Dict, Any, List

from src.agent_traccrop.config import AUTH_SERVER_URL

import os
import time

class AuthManager:
    def __init__(self):
        self.user_id = None
        self.access_token = None
        self.user_name = "User"
        self.account_id = None
        self.privileges: List[str] = []

    def load_cached_token(self) -> bool:
        if os.path.exists(".auth_token"):
            with open(".auth_token", "r") as f:
                token = f.read().strip()
            try:
                decoded = jwt.decode(token, options={"verify_signature": False})
                if decoded.get("exp", 0) > time.time():
                    self.access_token = token
                    self.user_id = str(decoded.get("user_id"))
                    return True
            except Exception:
                pass
        return False

    def login(self) -> str:
        """Prompts for credentials, logs in, and decodes JWT. Restores from cache if available."""
        if self.load_cached_token():
            print("Session restored from cache.")
            return self.user_id
            
        print("=== CropTrac Agent Login ===")
        email = input("Email [traccrops+Tsowner@gmail.com]: ") or "traccrops+Tsowner@gmail.com"
        password = getpass.getpass("Password [billTE$T1]: ") or "billTE$T1"
        
        try:
            response = requests.post(
                f"{AUTH_SERVER_URL}/api/login",
                json={"email": email, "password": password},
                timeout=10
            )
            response.raise_for_status()
            auth_data = response.json()
            self.access_token = auth_data.get("success", {}).get("access")
            
            if not self.access_token:
                raise ValueError("No access token received.")
                
            decoded_payload = jwt.decode(self.access_token, options={"verify_signature": False})
            self.user_id = str(decoded_payload.get("user_id"))
            
            if not self.user_id or self.user_id == "None":
                raise ValueError("Token missing user_id field.")
                
            with open(".auth_token", "w") as f:
                f.write(self.access_token)
                
            print("\nLogin successful!")
            return self.user_id
        except Exception as e:
            print(f"\nLogin failed: {e}")
            exit(1)

    def load_user_info(self):
        """Fetches additional user info (name, account ID, privileges) from the Auth API."""
        if not self.access_token:
            return
            
        try:
            # We call the provided auth endpoint
            auth_url = f"{AUTH_SERVER_URL}/api/auth"
            response = requests.get(
                auth_url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10
            )
            response.raise_for_status()
            user_data = response.json().get("success", {})
            
            self.user_name = user_data.get("username", self.user_name)
            self.account_id = user_data.get("account_id")
            self.privileges = user_data.get("privileges", [])
            
        except Exception as e:
            print(f"Warning: Failed to load extended user info from Auth API: {e}")