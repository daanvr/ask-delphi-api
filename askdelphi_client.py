import os
import json
import time
import uuid
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional
import requests
from dotenv import load_dotenv

class AskDelphiClient:
    PORTAL_SERVER = "https://portal.askdelphi.com"

    def __init__(self, portal_code: Optional[str] = None, token_cache=".askdelphi_tokens.json"):
        load_dotenv()

        self.portal_code = portal_code or os.getenv("ASKDELPHI_PORTAL_CODE")
        self.token_cache_file = token_cache

        self._access_token = None
        self._refresh_token = None
        self._publication_url = None
        self._api_token = None
        self._api_token_expiry = 0

        self._load_tokens()

    # ----------------------------------------------------------
    # SIMPLE AUTHENTICATION
    # ----------------------------------------------------------
    def authenticate(self, portal_code: Optional[str] = None):
        print("="*60)
        print("AUTHENTICATION STARTED")
        print("="*60)

        # Try cached API token
        if self._access_token and self._publication_url:
            print("Trying cached tokens...")
            try:
                self._get_api_token()
                print("SUCCESS using cached tokens!")
                return True
            except Exception as e:
                print("Cached tokens failed:", e)

        code = portal_code or self.portal_code
        if not code:
            raise ValueError("No portal code provided and none found in environment.")

        print("Exchanging portal code...")
        url = f"{self.PORTAL_SERVER}/api/session/registration?sessionCode={code}"

        response = requests.get(url, headers={"Accept": "application/json"})
        print("Status:", response.status_code)

        if not response.ok:
            raise Exception(f"Portal authentication failed:\n{response.text}")

        data = response.json()
        self._access_token = data.get("accessToken")
        self._refresh_token = data.get("refreshToken")

        full_url = data.get("url")
        if not full_url:
            raise Exception("Portal did not return publication URL")

        parsed = urlparse(full_url)
        self._publication_url = f"{parsed.scheme}://{parsed.netloc}"

        if not self._access_token:
            raise Exception("Portal returned no access token.")

        print("Access token received.")
        print("Publication URL:", self._publication_url)

        self._save_tokens()

        print("Getting editing API token...")
        self._get_api_token()

        print("="*60)
        print("AUTHENTICATION SUCCESSFUL")
        print("="*60)
        return True

    # ----------------------------------------------------------
    # SIMPLE GET API TOKEN
    # ----------------------------------------------------------
    def _get_api_token(self):
        if self._api_token and time.time() < self._api_token_expiry - 300:
            return self._api_token

        if not self._access_token or not self._publication_url:
            raise Exception("Call authenticate() first")

        url = f"{self._publication_url}/api/token/EditingApiToken"
        headers = {"Authorization": f"Bearer {self._access_token}", "Accept": "application/json"}

        response = requests.get(url, headers=headers)
        print("Editing API token status:", response.status_code)

        if not response.ok:
            raise Exception(f"Failed to fetch editing API token:\n{response.text}")

        token = response.text.strip().strip('"')
        self._api_token = token

        # Parse JWT expiry
        try:
            import base64
            payload = token.split(".")[1]
            payload += "=" * (4 - len(payload) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            self._api_token_expiry = decoded.get("exp", time.time() + 3600)
        except Exception:
            self._api_token_expiry = time.time() + 3600

        print("Editing API token acquired.")
        return self._api_token

    # ----------------------------------------------------------
    # TOKEN CACHE
    # ----------------------------------------------------------
    def _save_tokens(self):
        Path(self.token_cache_file).write_text(json.dumps({
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "publication_url": self._publication_url
        }))
        print("Tokens saved to cache.")

    def _load_tokens(self):
        path = Path(self.token_cache_file)
        if not path.exists():
            return

        data = json.loads(path.read_text())
        self._access_token = data.get("access_token")
        self._refresh_token = data.get("refresh_token")
        self._publication_url = data.get("publication_url")
        print("Loaded cached tokens.")

    # ----------------------------------------------------------
    # SIMPLE TEST CALL (optional)
    # ----------------------------------------------------------
    def test_call(self):
        """Use the editing API token to confirm everything works."""
        token = self._get_api_token()
        print("JWT begins with:", token[:20], "...")
        print("Ready for API operations!")


print("AskDelphi Client loaded.")