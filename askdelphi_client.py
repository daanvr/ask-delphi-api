import os
import json
import re
import uuid
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
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

        # Build URL with tenant/project/acl
        url = (
            f"{self.API_SERVER}/{endpoint}"
            .replace("{tenantId}", self.tenant_id)
            .replace("{projectId}", self.project_id)
            .replace("{aclEntryId}", self.acl_entry_id)
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AskDelphi-Python-Client/1.0"
        }

        log_request(method, url, headers, json_data)

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=60
            )
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

        log_response(response)

        if not response.ok:
            error_msg = self._format_error_response(response, f"API {method} {endpoint}")
            logger.error(error_msg)
            raise Exception(error_msg)

        data = response.json()

        # Handle wrapped response
        if isinstance(data, dict) and "success" in data:
            if not data.get("success"):
                error_msg = f"API error: {data.get('errorMessage', 'Unknown error')}"
                logger.error(error_msg)
                raise Exception(error_msg)
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
        logger.info("Getting content design...")
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
        logger.info(f"Searching topics: query='{query}', limit={limit}, offset={offset}")

        # Calculate page number from offset
        page = offset // limit if limit > 0 else 0

        body = {
            "query": query,
            "page": page,
            "pageSize": limit,
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
        logger.info(f"Creating topic: '{title}' (type: {topic_type_id})")
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
        logger.info(f"Getting topic parts: {topic_id}")
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
        logger.info(f"Updating topic part: {topic_id} / {part_id}")
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
        logger.info(f"Checking out topic: {topic_id}")
        endpoint = (
            f"v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
            f"/topic/{topic_id}/workflowstate"
        )
        body = {
            "action": 0,
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
        logger.info(f"Checking in topic: {topic_id}")
        endpoint = (
            f"v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
            f"/topic/{topic_id}/workflowstate"
        )
        body = {
            "action": 1,
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
        logger.info(f"Getting workflow state: {topic_id}")
        endpoint = (
            f"v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
            f"/topic/{topic_id}/workflowstate"
        )
        return self._request("GET", endpoint)

    # =========================================================================
    # Bulk Operations (for content sync)
    # =========================================================================

    def get_all_topics(
        self,
        topic_type_ids: Optional[List[str]] = None,
        page_size: int = 50,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Get ALL topics with automatic pagination.

        Args:
            topic_type_ids: Optional filter by topic type IDs
            page_size: Number of topics per API call
            progress_callback: Optional callback(current, total) for progress

        Returns:
            List of all topic dictionaries
        """
        logger.info("Fetching all topics...")
        all_topics = []
        offset = 0
        total = 0  # Will be updated from API response

        while True:
            result = self.search_topics(
                query="",
                topic_type_ids=topic_type_ids,
                limit=page_size,
                offset=offset
            )

            # Handle different response structures
            # API returns: { "topicList": { "result": [...], "totalAvailable": N } }
            topic_list = result.get("topicList", {})
            if topic_list:
                items = topic_list.get("result", [])
                total = topic_list.get("totalAvailable", 0)
            else:
                # Fallback for other response formats
                items = result.get("items", result.get("data", result.get("result", [])))
                total = result.get("total", result.get("totalCount", result.get("totalAvailable", 0)))

            all_topics.extend(items)

            if progress_callback:
                progress_callback(len(all_topics), total)

            logger.debug(f"Fetched {len(all_topics)}/{total} topics (page returned {len(items)} items)")

            # Stop ONLY when we get an empty page - don't trust totalAvailable
            if not items:
                logger.debug("Received empty page, stopping pagination")
                break

            offset += page_size

        logger.info(f"Total topics fetched: {len(all_topics)} (API reported total: {total})")
        return all_topics

    def get_topic_full(
        self,
        topic_id: str,
        topic_version_id: str
    ) -> Dict[str, Any]:
        """
        Get complete topic data including parts.

        Args:
            topic_id: Topic GUID
            topic_version_id: Topic version GUID

        Returns:
            Complete topic data with parts
        """
        parts = self.get_topic_parts(topic_id, topic_version_id)
        return {
            "topic_id": topic_id,
            "topic_version_id": topic_version_id,
            "parts": parts
        }

    def is_topic_checked_out(self, topic_id: str) -> tuple:
        """
        Check if a topic is currently checked out.

        Args:
            topic_id: Topic GUID

        Returns:
            Tuple of (is_checked_out: bool, checked_out_by: Optional[str])
        """
        try:
            state = self.get_topic_workflow_state(topic_id)
            is_checked_out = state.get("state", "").lower() == "checkedout"
            checked_out_by = state.get("checkedOutBy") if is_checked_out else None
            return is_checked_out, checked_out_by
        except Exception as e:
            logger.warning(f"Could not get workflow state for {topic_id}: {e}")
            return False, None

    def cancel_checkout(
        self,
        topic_id: str,
        topic_version_id: str
    ) -> Dict[str, Any]:
        """
        Cancel a checkout (discard changes).

        Args:
            topic_id: Topic GUID
            topic_version_id: Topic version GUID

        Returns:
            Cancel result
        """
        logger.info(f"Cancelling checkout: {topic_id}")
        endpoint = (
            f"v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
            f"/topic/{topic_id}/workflowstate"
        )
        body = {
            "action": 2,
            "topicVersionId": topic_version_id,
        }
        return self._request("POST", endpoint, json_data=body)

    def update_topic_metadata(
        self,
        topic_id: str,
        topic_version_id: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update topic metadata like title.

        Args:
            topic_id: Topic GUID
            topic_version_id: Topic version GUID
            title: New title (optional)

        Returns:
            Update result
        """
        logger.info(f"Updating topic metadata: {topic_id}")
        endpoint = (
            f"v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
            f"/topic/{topic_id}/topicVersion/{topic_version_id}"
        )
        body = {}
        if title:
            body["title"] = title
        return self._request("PUT", endpoint, json_data=body)

    # =========================================================================
    # Topic Relations
    # =========================================================================

    def get_topic_relations(self, topic_id: str) -> Dict[str, Any]:
        """
        Get outgoing relations (children) for a topic.

        Args:
            topic_id: Topic GUID

        Returns:
            Dict with 'relations' list containing child topics
        """
        logger.debug(f"Getting outgoing relations for: {topic_id}")
        endpoint = (
            f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
            f"/topic/{topic_id}/relation"
        )
        return self._request("GET", endpoint)

    def get_topic_relations_categorized(self, topic_id: str) -> Dict[str, Any]:
        """
        Get outgoing relations organized by pyramid levels.

        Args:
            topic_id: Topic GUID

        Returns:
            Dict with 'pyramidLevels' list containing hierarchical relations
        """
        logger.debug(f"Getting categorized relations for: {topic_id}")
        endpoint = (
            f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
            f"/topic/{topic_id}/relation/categorized"
        )
        return self._request("GET", endpoint)

    def get_incoming_relations(
        self,
        topic_id: str,
        topic_version_id: str,
        page: int = 0,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Get incoming relations (parents) for a topic.

        Args:
            topic_id: Topic GUID
            topic_version_id: Topic version GUID
            page: Page number (0-based)
            page_size: Number of results per page

        Returns:
            Dict with 'data' containing parent topics that link to this topic
        """
        logger.debug(f"Getting incoming relations for: {topic_id}")
        endpoint = (
            f"v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
            f"/topic/{topic_id}/topicVersion/{topic_version_id}/incomingrelations/search"
        )
        body = {
            "page": page,
            "pageSize": page_size
        }
        return self._request("POST", endpoint, json_data=body)

    def delete_topic(self, topic_id: str, topic_version_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete (mark as deleted) a topic.

        The DELETE endpoint "marks the topic as deleted and checks-in topic",
        which means the topic must be checked out first before deletion.
        This method automatically handles checkout before delete.

        Args:
            topic_id: Topic GUID
            topic_version_id: Topic version GUID (optional, will checkout if not provided)

        Returns:
            Delete result
        """
        logger.info(f"Deleting topic: {topic_id}")

        # Step 1: Check out the topic to get a working version
        # The DELETE endpoint requires the topic to be checked out first
        # because it "marks as deleted and checks-in"
        try:
            logger.info(f"Checking out topic before delete: {topic_id}")
            checkout_result = self.checkout_topic(topic_id)
            # Use the new version ID from checkout
            topic_version_id = checkout_result
            logger.info(f"Checked out, got version: {topic_version_id}")
        except Exception as e:
            logger.warning(f"Checkout failed (topic may already be checked out): {e}")
            # If checkout fails, the topic might already be checked out by us
            # Try to get the current workflow state to get the version ID
            if not topic_version_id:
                try:
                    state = self.get_topic_workflow_state(topic_id)
                    topic_version_id = state.get("topicVersionId") or state.get("topicVersionKey")
                    logger.info(f"Got version from workflow state: {topic_version_id}")
                except Exception as e2:
                    logger.warning(f"Could not get workflow state: {e2}")

        if topic_version_id:
            # Try v3 endpoint first with empty body
            endpoint = (
                f"v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
                f"/topic/{topic_id}/topicVersion/{topic_version_id}"
            )
            # v3 expects DeleteTopicV3Request with optional workflowActions
            body = {}
            try:
                return self._request("DELETE", endpoint, json_data=body)
            except Exception as e:
                logger.warning(f"v3 delete failed, trying v2: {e}")

            # Fallback to v2 endpoint
            endpoint = (
                f"v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
                f"/topic/{topic_id}/topicVersion/{topic_version_id}"
            )
            # v2 expects DeleteTopicV2Request with optional workflow stage/transition ids
            body = {}
            return self._request("DELETE", endpoint, json_data=body)
        else:
            # Fallback to v1 endpoint (may fail for some topics)
            endpoint = (
                f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
                f"/topic/{topic_id}"
            )
            return self._request("DELETE", endpoint)


# Example usage
if __name__ == "__main__":
    print("AskDelphi Client - Run test_api.py for examples")
    print(f"Debug log file: askdelphi_debug.log")
