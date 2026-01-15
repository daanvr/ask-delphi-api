"""
Ask Delphi API Client

A simple Python client for the Ask Delphi Content API.
"""

import os
import json
import uuid
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

import requests
from dotenv import load_dotenv


class AskDelphiClient:
    """
    Client for communicating with the Ask Delphi Content API.

    Usage:
        client = AskDelphiClient()
        client.authenticate()
        design = client.get_content_design()
    """

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        acl_entry_id: Optional[str] = None,
        portal_code: Optional[str] = None,
        api_server: str = "https://edit.api.askdelphi.com/",
        portal_server: str = "https://portal.askdelphi.com/",
        token_cache_file: str = ".askdelphi_tokens.json"
    ):
        """
        Initialize the client.

        Args:
            tenant_id: Your tenant ID (from CMS URL or .env)
            project_id: Your project ID (from CMS URL or .env)
            acl_entry_id: Your ACL entry ID (from CMS URL or .env)
            portal_code: One-time portal code from Mobile tab (or .env)
            api_server: API server URL
            portal_server: Portal server URL
            token_cache_file: File to cache tokens in
        """
        # Load environment variables
        load_dotenv()

        # Use provided values or fall back to environment
        self.tenant_id = tenant_id or os.getenv("ASKDELPHI_TENANT_ID")
        self.project_id = project_id or os.getenv("ASKDELPHI_PROJECT_ID")
        self.acl_entry_id = acl_entry_id or os.getenv("ASKDELPHI_ACL_ENTRY_ID")
        self.portal_code = portal_code or os.getenv("ASKDELPHI_PORTAL_CODE")
        self.api_server = os.getenv("ASKDELPHI_API_SERVER", api_server).rstrip("/") + "/"
        self.portal_server = os.getenv("ASKDELPHI_PORTAL_SERVER", portal_server).rstrip("/") + "/"
        self.token_cache_file = token_cache_file

        # Validate required fields
        if not all([self.tenant_id, self.project_id, self.acl_entry_id]):
            raise ValueError(
                "Missing required credentials. Provide tenant_id, project_id, and acl_entry_id "
                "either as arguments or in .env file."
            )

        # Token storage
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._publication_url: Optional[str] = None
        self._api_token: Optional[str] = None
        self._api_token_expiry: float = 0

        # Try to load cached tokens
        self._load_tokens()

    # =========================================================================
    # Authentication
    # =========================================================================

    def authenticate(self, portal_code: Optional[str] = None) -> bool:
        """
        Authenticate with the API.

        First tries to use cached tokens. If not available or expired,
        uses the portal code to get new tokens.

        Args:
            portal_code: Optional portal code to use (overrides stored code)

        Returns:
            True if authentication successful
        """
        # Try to get API token with existing tokens
        if self._access_token and self._publication_url:
            try:
                self._get_api_token()
                print("Authenticated using cached tokens")
                return True
            except Exception:
                pass  # Fall through to portal code auth

        # Use portal code
        code = portal_code or self.portal_code
        if not code:
            raise ValueError(
                "No portal code available. Provide one via argument, "
                "constructor, or ASKDELPHI_PORTAL_CODE in .env"
            )

        # Exchange portal code for tokens
        print(f"Exchanging portal code for tokens...")
        url = f"{self.portal_server}api/session/registration?sessionCode={code}"
        print(f"  URL: {url}")

        try:
            response = requests.get(url, timeout=30)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error connecting to portal: {e}")

        # Debug info
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type', 'unknown')}")

        if not response.ok:
            # Try to get error message
            try:
                error_text = response.text[:500]
            except Exception:
                error_text = f"(could not decode response)"
            raise Exception(f"Failed to exchange portal code: {response.status_code}\n  Response: {error_text}")

        # Check if response is JSON
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type and 'text/json' not in content_type:
            # Try to show what we got
            try:
                preview = response.text[:200]
            except Exception:
                preview = f"(binary data, first bytes: {response.content[:20]})"
            raise Exception(
                f"Expected JSON response but got Content-Type: {content_type}\n"
                f"  Response preview: {preview}\n"
                f"  This might mean the portal code is invalid or expired."
            )

        try:
            data = response.json()
        except ValueError as e:
            raise Exception(f"Failed to parse JSON response: {e}\n  Response: {response.text[:500]}")
        self._access_token = data.get("accessToken")
        self._refresh_token = data.get("refreshToken")
        self._publication_url = data.get("url", "").rstrip("/")

        if not all([self._access_token, self._refresh_token, self._publication_url]):
            raise Exception(f"Invalid response from portal: {data}")

        # Save tokens
        self._save_tokens()

        # Get API token
        self._get_api_token()

        print("Authentication successful!")
        return True

    def _get_api_token(self) -> str:
        """Get or refresh the API token."""
        # Check if we have a valid token
        if self._api_token and time.time() < self._api_token_expiry - 300:  # 5 min buffer
            return self._api_token

        # Try to refresh if token is expired
        if self._refresh_token and time.time() >= self._api_token_expiry - 300:
            try:
                self._refresh_tokens()
            except Exception:
                pass  # Will try with current access token

        # Get new API token
        if not self._access_token or not self._publication_url:
            raise Exception("No access token available. Call authenticate() first.")

        url = f"{self._publication_url}/api/token/EditingApiToken"
        headers = {"Authorization": f"Bearer {self._access_token}"}

        response = requests.get(url, headers=headers)
        if not response.ok:
            raise Exception(f"Failed to get API token: {response.status_code} {response.text}")

        token = response.text.strip().strip('"')

        # Parse JWT expiry (simple base64 decode of payload)
        import base64
        payload = token.split(".")[1]
        # Add padding if needed
        payload += "=" * (4 - len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload))

        self._api_token = token
        self._api_token_expiry = decoded.get("exp", time.time() + 3600)

        return self._api_token

    def _refresh_tokens(self):
        """Refresh the access token using refresh token."""
        if not self._refresh_token or not self._publication_url:
            raise Exception("No refresh token available")

        url = (
            f"{self._publication_url}/api/token/refresh"
            f"?token={self._access_token}&refreshToken={self._refresh_token}"
        )

        response = requests.get(url)
        if not response.ok:
            raise Exception(f"Failed to refresh token: {response.status_code}")

        data = response.json()
        self._access_token = data.get("accessToken", self._access_token)
        self._refresh_token = data.get("refreshToken", self._refresh_token)

        self._save_tokens()

    def _save_tokens(self):
        """Save tokens to cache file."""
        data = {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "publication_url": self._publication_url,
        }
        Path(self.token_cache_file).write_text(json.dumps(data, indent=2))

    def _load_tokens(self):
        """Load tokens from cache file."""
        try:
            path = Path(self.token_cache_file)
            if path.exists():
                data = json.loads(path.read_text())
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")
                self._publication_url = data.get("publication_url")
        except Exception:
            pass  # Ignore errors, will authenticate fresh

    # =========================================================================
    # API Request Helper
    # =========================================================================

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make an authenticated API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            json_data: JSON body for POST/PUT
            params: Query parameters

        Returns:
            Response data from API
        """
        token = self._get_api_token()

        # Build URL with tenant/project/acl
        url = (
            f"{self.api_server}{endpoint}"
            .replace("{tenantId}", self.tenant_id)
            .replace("{projectId}", self.project_id)
            .replace("{aclEntryId}", self.acl_entry_id)
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
            params=params
        )

        if not response.ok:
            raise Exception(f"API request failed: {response.status_code} {response.text}")

        data = response.json()

        # Handle wrapped response
        if isinstance(data, dict) and "success" in data:
            if not data.get("success"):
                raise Exception(f"API error: {data.get('errorMessage', 'Unknown error')}")
            return data.get("response", data)

        return data

    # =========================================================================
    # Content Design
    # =========================================================================

    def get_content_design(self) -> Dict[str, Any]:
        """
        Get the content design (topic types, relations, etc.) for the project.

        Returns:
            Content design with topicTypes, relations, etc.
        """
        return self._request(
            "GET",
            "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/contentdesign"
        )

    # =========================================================================
    # Topic Search
    # =========================================================================

    def search_topics(
        self,
        query: str = "",
        topic_type_ids: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search for topics.

        Args:
            query: Search query
            topic_type_ids: Filter by topic type IDs
            limit: Max results to return
            offset: Pagination offset

        Returns:
            Search results with items and pagination info
        """
        body = {
            "query": query,
            "skip": offset,
            "take": limit,
        }
        if topic_type_ids:
            body["topicTypeIds"] = topic_type_ids

        return self._request(
            "POST",
            "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topiclist",
            json_data=body
        )

    # =========================================================================
    # Topic CRUD
    # =========================================================================

    def create_topic(
        self,
        title: str,
        topic_type_id: str,
        copy_parent_tags: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new topic.

        Args:
            title: Topic title
            topic_type_id: GUID of the topic type
            copy_parent_tags: Whether to copy tags from parent

        Returns:
            Created topic with topicId and topicVersionKey
        """
        body = {
            "topicId": str(uuid.uuid4()),
            "topicTitle": title,
            "topicTypeId": topic_type_id,
            "copyParentTags": copy_parent_tags,
        }

        return self._request(
            "POST",
            "v4/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic",
            json_data=body
        )

    def get_topic_parts(
        self,
        topic_id: str,
        topic_version_id: str
    ) -> Dict[str, Any]:
        """
        Get all content parts for a topic.

        Args:
            topic_id: Topic GUID
            topic_version_id: Topic version GUID

        Returns:
            Topic parts with groups and editors
        """
        endpoint = (
            f"v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
            f"/topic/{topic_id}/topicVersion/{topic_version_id}/part"
        )
        return self._request("GET", endpoint)

    def update_topic_part(
        self,
        topic_id: str,
        topic_version_id: str,
        part_id: str,
        part_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a topic content part.

        Args:
            topic_id: Topic GUID
            topic_version_id: Topic version GUID
            part_id: Part ID to update
            part_data: New part data

        Returns:
            Update result
        """
        endpoint = (
            f"v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
            f"/topic/{topic_id}/topicVersion/{topic_version_id}/part/{part_id}"
        )
        body = {"part": part_data}
        return self._request("PUT", endpoint, json_data=body)

    # =========================================================================
    # Workflow
    # =========================================================================

    def checkout_topic(self, topic_id: str) -> str:
        """
        Check out a topic for editing.

        Args:
            topic_id: Topic GUID

        Returns:
            New topic version ID for editing
        """
        endpoint = (
            f"v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
            f"/topic/{topic_id}/workflowstate"
        )
        body = {
            "action": "CheckOut",
        }
        result = self._request("POST", endpoint, json_data=body)
        return result.get("topicVersionId") or result.get("topicVersionKey")

    def checkin_topic(
        self,
        topic_id: str,
        topic_version_id: str,
        apply_to_default_stage: bool = True
    ) -> Dict[str, Any]:
        """
        Check in a topic after editing.

        Args:
            topic_id: Topic GUID
            topic_version_id: Topic version GUID
            apply_to_default_stage: Apply to default editing stage

        Returns:
            Check-in result
        """
        endpoint = (
            f"v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
            f"/topic/{topic_id}/workflowstate"
        )
        body = {
            "action": "CheckIn",
            "topicVersionId": topic_version_id,
            "applyToDefaultStage": apply_to_default_stage,
        }
        return self._request("POST", endpoint, json_data=body)

    def get_topic_workflow_state(self, topic_id: str) -> Dict[str, Any]:
        """
        Get the current workflow state of a topic.

        Args:
            topic_id: Topic GUID

        Returns:
            Workflow state info
        """
        endpoint = (
            f"v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
            f"/topic/{topic_id}/workflowstate"
        )
        return self._request("GET", endpoint)


# Example usage
if __name__ == "__main__":
    print("AskDelphi Client - Run test_api.py for examples")
