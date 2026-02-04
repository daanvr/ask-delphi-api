import re
from typing import Tuple, Dict
import os, json, time
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional
import requests
from dotenv import load_dotenv

def parse_cms_url(url: str) -> Tuple[str, str, str]:
    pattern = r"/tenant/([a-f0-9-]+)/project/([a-f0-9-]+)/acl/([a-f0-9-]+)"
    match = re.search(pattern, url, re.IGNORECASE)

    if not match:
        raise ValueError(
            f"Could not parse CMS URL: {url}\n"
            "Expected format: https://xxx.askdelphi.com/cms/tenant/{TENANT_ID}/project/{PROJECT_ID}/acl/{ACL_ENTRY_ID}/..."
        )
    return match.group(1), match.group(2), match.group(3)


class AskDelphiClient:
    PORTAL_SERVER = "https://portal.askdelphi.com"

    def __init__(
            self,
            cms_url: Optional[str] = None,
            tenant_id: Optional[str] = None,
            project_id: Optional[str] = None,
            acl_entry_id: Optional[str] = None,
            portal_code: Optional[str] = None, 
            token_cache=".askdelphi_tokens.json"
            ):
        load_dotenv(override=True)
        cms_url = cms_url or os.getenv("ASKDELPHI_CMS_URL")
        if cms_url:
            try: 
                self.tenant_id, self.project_id, self.acl_entry_id = parse_cms_url(cms_url)
                print("Parsed tenant/project/acl from CMS URL")
            except ValueError:
                print("could not find tenant/project and/or acl")

        
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
    # GENERIC API REQUEST
    # ----------------------------------------------------------
    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ):
        """Perform an authenticated request to the AskDelphi Editing API."""

        # Ensure we have a valid editing token
        token = self._get_api_token()

        # Ensure required identifiers exist
        for attr in ["tenant_id", "project_id", "acl_entry_id"]:
            if not hasattr(self, attr) or getattr(self, attr) is None:
                raise ValueError(
                    f"{attr} is not set. Provide cms_url or explicit IDs to the constructor."
                )

        # Replace placeholders
        path = (
            endpoint
            .replace("{tenantId}", self.tenant_id)
            .replace("{projectId}", self.project_id)
            .replace("{aclEntryId}", self.acl_entry_id)
            .lstrip("/")
        )

        # API endpoint
        url = f"https://edit.api.askdelphi.com/{path}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AskDelphi-Python-Client/1.0"
        }

        # Debug prints
        print("\n" + "=" * 60)
        print(f"REQUEST: {method} {url}")
        if params:
            print("Params:", params)
        if json_data:
            print("JSON body:", json.dumps(json_data, indent=2, ensure_ascii=False)[:2000])

        # Execute HTTP request
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=60
            )
        except Exception as e:
            print("Network error:", e)
            raise

        print(f"RESPONSE: {response.status_code} {response.reason}")

        # Error handling
        if not response.ok:
            print("Body:", response.text[:500])
            if response.status_code == 401:
                print("401 Unauthorized - token expired? Try authenticate() again.")
            elif response.status_code == 403:
                print("403 Forbidden - insufficient ACL permissions.")
            elif response.status_code == 404:
                print("404 Not Found - check endpoint and placeholders.")
            raise Exception(f"API error {response.status_code}: {response.text}")

        # Try JSON
        try:
            return response.json()
        except Exception:
            print("Non-JSON response returned as raw text.")
            return {"raw": response.text}

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