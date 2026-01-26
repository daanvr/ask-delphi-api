"""
Ask Delphi API Client

A Python client for the Ask Delphi Content API.
"""

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

import requests
from dotenv import load_dotenv


def parse_cms_url(url: str) -> Tuple[str, str, str]:
    """
    Parse an Ask Delphi CMS URL and extract tenant_id, project_id, acl_entry_id.

    URL format:
    https://xxx.askdelphi.com/cms/tenant/{TENANT_ID}/project/{PROJECT_ID}/acl/{ACL_ENTRY_ID}/...

    Args:
        url: The CMS URL from the browser

    Returns:
        Tuple of (tenant_id, project_id, acl_entry_id)

    Raises:
        ValueError: If URL cannot be parsed
    """
    pattern = r'/tenant/([a-f0-9-]+)/project/([a-f0-9-]+)/acl/([a-f0-9-]+)'
    match = re.search(pattern, url, re.IGNORECASE)

    if not match:
        raise ValueError(
            f"Could not parse CMS URL: {url}\n"
            "Expected format: https://xxx.askdelphi.com/cms/tenant/{{TENANT_ID}}/project/{{PROJECT_ID}}/acl/{{ACL_ENTRY_ID}}/..."
        )

    return match.group(1), match.group(2), match.group(3)


# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging(log_file: str = "askdelphi_debug.log", verbose: bool = True):
    """
    Setup logging to both console and file.

    Args:
        log_file: Path to log file
        verbose: If True, also print DEBUG to console
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler - always verbose
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(formatter)

    # Setup logger
    logger = logging.getLogger('askdelphi')
    logger.setLevel(logging.DEBUG)
    logger.handlers = []  # Clear existing handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Global logger
logger = setup_logging()


def log_request(method: str, url: str, headers: dict = None, body: any = None):
    """Log outgoing request details."""
    logger.debug(f"{'='*60}")
    logger.debug(f"REQUEST: {method} {url}")
    if headers:
        safe_headers = {k: (v[:50] + '...' if k.lower() == 'authorization' and len(v) > 50 else v)
                       for k, v in headers.items()}
        logger.debug(f"Headers: {json.dumps(safe_headers, indent=2)}")
    if body:
        logger.debug(f"Body: {json.dumps(body, indent=2, default=str)}")


def log_response(response: requests.Response):
    """Log incoming response details."""
    logger.debug(f"RESPONSE: {response.status_code} {response.reason}")
    logger.debug(f"Headers: {dict(response.headers)}")

    # Try to log body
    try:
        content_type = response.headers.get('Content-Type', '')
        if 'json' in content_type:
            try:
                body = response.json()
                logger.debug(f"Body (JSON): {json.dumps(body, indent=2, default=str)[:2000]}")
            except:
                logger.debug(f"Body (text): {response.text[:2000]}")
        elif 'text' in content_type or 'html' in content_type:
            logger.debug(f"Body (text): {response.text[:2000]}")
        else:
            logger.debug(f"Body (binary): {response.content[:200]}")
    except Exception as e:
        logger.debug(f"Could not log response body: {e}")

    logger.debug(f"{'='*60}")


class AskDelphiClient:
    """
    Client for communicating with the Ask Delphi Content API.

    Usage:
        client = AskDelphiClient()
        client.authenticate()
        design = client.get_content_design()
    """

    # Portal server is ALWAYS portal.askdelphi.com
    # The company-specific URL comes back AFTER authentication
    PORTAL_SERVER = "https://portal.askdelphi.com"
    API_SERVER = "https://edit.api.askdelphi.com"

    def __init__(
        self,
        cms_url: Optional[str] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        acl_entry_id: Optional[str] = None,
        portal_code: Optional[str] = None,
        token_cache_file: str = ".askdelphi_tokens.json"
    ):
        """
        Initialize the client.

        Args:
            cms_url: Full CMS URL containing tenant/project/acl IDs (easiest option)
            tenant_id: Your tenant ID (fallback if cms_url not provided)
            project_id: Your project ID (fallback if cms_url not provided)
            acl_entry_id: Your ACL entry ID (fallback if cms_url not provided)
            portal_code: One-time portal code from Mobile tab (or .env)
            token_cache_file: File to cache tokens in
        """
        logger.info("Initializing AskDelphiClient...")

        # Load environment variables
        load_dotenv()

        # Try to get IDs from CMS URL first (easiest option)
        cms_url = cms_url or os.getenv("ASKDELPHI_CMS_URL")

        if cms_url:
            try:
                parsed_tenant, parsed_project, parsed_acl = parse_cms_url(cms_url)
                logger.info(f"  Parsed IDs from CMS URL")
                self.tenant_id = tenant_id or parsed_tenant
                self.project_id = project_id or parsed_project
                self.acl_entry_id = acl_entry_id or parsed_acl
            except ValueError as e:
                logger.warning(f"Could not parse CMS URL: {e}")
                # Fall back to individual variables
                self.tenant_id = tenant_id or os.getenv("ASKDELPHI_TENANT_ID")
                self.project_id = project_id or os.getenv("ASKDELPHI_PROJECT_ID")
                self.acl_entry_id = acl_entry_id or os.getenv("ASKDELPHI_ACL_ENTRY_ID")
        else:
            # Use individual variables
            self.tenant_id = tenant_id or os.getenv("ASKDELPHI_TENANT_ID")
            self.project_id = project_id or os.getenv("ASKDELPHI_PROJECT_ID")
            self.acl_entry_id = acl_entry_id or os.getenv("ASKDELPHI_ACL_ENTRY_ID")

        self.portal_code = portal_code or os.getenv("ASKDELPHI_PORTAL_CODE")
        self.token_cache_file = token_cache_file

        # Log configuration
        logger.info(f"  Tenant ID: {self.tenant_id}")
        logger.info(f"  Project ID: {self.project_id}")
        logger.info(f"  ACL Entry ID: {self.acl_entry_id}")
        logger.info(f"  Portal Code: {self.portal_code[:4]}...{self.portal_code[-4:] if self.portal_code and len(self.portal_code) > 8 else self.portal_code}")
        logger.info(f"  Portal Server: {self.PORTAL_SERVER}")
        logger.info(f"  API Server: {self.API_SERVER}")

        # Validate required fields
        missing = []
        if not self.tenant_id:
            missing.append("ASKDELPHI_TENANT_ID (or ASKDELPHI_CMS_URL)")
        if not self.project_id:
            missing.append("ASKDELPHI_PROJECT_ID (or ASKDELPHI_CMS_URL)")
        if not self.acl_entry_id:
            missing.append("ASKDELPHI_ACL_ENTRY_ID (or ASKDELPHI_CMS_URL)")

        if missing:
            error_msg = f"Missing required credentials: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

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
        logger.info("="*60)
        logger.info("AUTHENTICATION STARTED")
        logger.info("="*60)

        # Try to get API token with existing tokens
        if self._access_token and self._publication_url:
            logger.info("Found cached tokens, trying to use them...")
            try:
                self._get_api_token()
                logger.info("SUCCESS: Authenticated using cached tokens")
                return True
            except Exception as e:
                logger.warning(f"Cached tokens failed: {e}")
                logger.info("Will try portal code authentication...")

        # Use portal code
        code = portal_code or self.portal_code
        if not code:
            error_msg = (
                "No portal code available. Provide one via:\n"
                "  - argument to authenticate()\n"
                "  - constructor parameter\n"
                "  - ASKDELPHI_PORTAL_CODE in .env file"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Step 1: Exchange portal code for tokens
        logger.info(f"Step 1: Exchanging portal code for tokens...")
        logger.info(f"  Portal code: {code}")

        url = f"{self.PORTAL_SERVER}/api/session/registration?sessionCode={code}"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",  # Explicitly handle compression
            "User-Agent": "AskDelphi-Python-Client/1.0"
        }

        log_request("GET", url, headers)

        try:
            # Use a session to handle compression properly
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=30)
        except requests.exceptions.Timeout:
            error_msg = f"Request timed out after 30 seconds"
            logger.error(error_msg)
            raise Exception(error_msg)
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

        log_response(response)

        # Log raw response info for debugging
        logger.debug(f"Response encoding: {response.encoding}")
        logger.debug(f"Response apparent_encoding: {response.apparent_encoding}")
        logger.debug(f"Content-Encoding header: {response.headers.get('Content-Encoding', 'none')}")
        logger.debug(f"Raw content first 100 bytes: {response.content[:100]}")

        if not response.ok:
            error_msg = self._format_error_response(response, "Portal code exchange")
            logger.error(error_msg)
            raise Exception(error_msg)

        # Parse response - handle potential encoding issues
        try:
            # First try the standard way
            data = response.json()
            logger.debug(f"Parsed JSON response: {json.dumps(data, indent=2)}")
        except (ValueError, UnicodeDecodeError) as e:
            logger.warning(f"Standard JSON parsing failed: {e}")

            # Try to decode manually with different approaches
            try:
                # Try decoding as utf-8 from raw content
                text = response.content.decode('utf-8')
                data = json.loads(text)
                logger.debug(f"Parsed JSON via manual utf-8 decode: {json.dumps(data, indent=2)}")
            except (UnicodeDecodeError, json.JSONDecodeError) as e2:
                logger.warning(f"Manual utf-8 decode failed: {e2}")

                # Try latin-1 (accepts any byte)
                try:
                    text = response.content.decode('latin-1')
                    data = json.loads(text)
                    logger.debug(f"Parsed JSON via latin-1 decode: {json.dumps(data, indent=2)}")
                except json.JSONDecodeError as e3:
                    # Log extensive debug info
                    logger.error(f"All JSON parsing attempts failed!")
                    logger.error(f"  Original error: {e}")
                    logger.error(f"  UTF-8 error: {e2}")
                    logger.error(f"  Latin-1 error: {e3}")
                    logger.error(f"  Raw content (hex): {response.content[:200].hex()}")
                    logger.error(f"  Raw content (repr): {repr(response.content[:200])}")

                    error_msg = (
                        f"Failed to parse JSON response from portal.\n"
                        f"  Content-Type: {response.headers.get('Content-Type', 'unknown')}\n"
                        f"  Content-Encoding: {response.headers.get('Content-Encoding', 'none')}\n"
                        f"  Response encoding: {response.encoding}\n"
                        f"  Raw bytes (first 50): {response.content[:50].hex()}\n"
                        f"  This might indicate the response is compressed or corrupted.\n"
                        f"  Check askdelphi_debug.log for full details."
                    )
                    raise Exception(error_msg)

        # Extract tokens
        self._access_token = data.get("accessToken")
        self._refresh_token = data.get("refreshToken")

        # IMPORTANT: Extract only the base URL (scheme + host) from the returned URL.
        # The portal returns a full URL with path like:
        #   https://company.askdelphi.com/nl-NL/Project/page/eyJMMSI6...
        # But we only need the base URL for API calls:
        #   https://company.askdelphi.com
        # This matches the C# implementation which does:
        #   $"{uri.Scheme}://{uri.Host}/api/token/EditingApiToken"
        full_url = data.get("url", "")
        if full_url:
            parsed = urlparse(full_url)
            self._publication_url = f"{parsed.scheme}://{parsed.netloc}"
        else:
            self._publication_url = ""

        logger.info(f"  Received access token: {self._access_token[:20] if self._access_token else 'None'}...")
        logger.info(f"  Received refresh token: {self._refresh_token[:20] if self._refresh_token else 'None'}...")
        logger.info(f"  Full URL from portal: {full_url}")
        logger.info(f"  Extracted base URL: {self._publication_url}")

        if not self._access_token:
            error_msg = f"No accessToken in portal response. Response was: {data}"
            logger.error(error_msg)
            raise Exception(error_msg)

        if not self._publication_url:
            error_msg = f"No url in portal response. Response was: {data}"
            logger.error(error_msg)
            raise Exception(error_msg)

        # Save tokens
        self._save_tokens()
        logger.info("  Tokens saved to cache file")

        # Step 2: Get API token
        logger.info(f"Step 2: Getting editing API token...")
        self._get_api_token()

        logger.info("="*60)
        logger.info("AUTHENTICATION SUCCESSFUL")
        logger.info("="*60)
        return True

    def _format_error_response(self, response: requests.Response, context: str) -> str:
        """Format a detailed error message from a failed response."""
        lines = [
            f"{context} failed!",
            f"",
            f"  Status Code: {response.status_code} {response.reason}",
            f"  URL: {response.url}",
            f"  Content-Type: {response.headers.get('Content-Type', 'unknown')}",
        ]

        # Try to get response body
        try:
            content_type = response.headers.get('Content-Type', '')
            if 'json' in content_type:
                try:
                    body = response.json()
                    lines.append(f"  Response (JSON): {json.dumps(body, indent=4)}")
                except:
                    lines.append(f"  Response (text): {response.text[:1000]}")
            else:
                lines.append(f"  Response (text): {response.text[:1000]}")
        except:
            lines.append(f"  Response: (could not decode)")

        # Add troubleshooting hints based on status code
        lines.append("")
        lines.append("Troubleshooting:")

        if response.status_code == 401:
            lines.append("  - 401 Unauthorized: The portal code may be invalid, expired, or already used.")
            lines.append("  - Portal codes are ONE-TIME USE. Get a fresh code from the Mobile tab.")
            lines.append("  - Make sure you're copying the full code (format: ABC123-XYZ789)")
        elif response.status_code == 404:
            lines.append("  - 404 Not Found: The endpoint doesn't exist at this URL.")
            lines.append("  - This might mean the portal server URL is wrong.")
            lines.append("  - The correct portal is always: https://portal.askdelphi.com")
        elif response.status_code == 403:
            lines.append("  - 403 Forbidden: Access denied. Check your permissions.")
        elif response.status_code >= 500:
            lines.append("  - 5xx Server Error: The server is having issues. Try again later.")

        return "\n".join(lines)

    def _get_api_token(self) -> str:
        """Get or refresh the API token."""
        logger.debug("Getting API token...")

        # Check if we have a valid token
        if self._api_token and time.time() < self._api_token_expiry - 300:
            logger.debug("Using cached API token (still valid)")
            return self._api_token

        # Try to refresh if token is expired
        if self._refresh_token and time.time() >= self._api_token_expiry - 300:
            logger.debug("API token expired or expiring soon, trying refresh...")
            try:
                self._refresh_tokens()
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}")

        # Get new API token
        if not self._access_token or not self._publication_url:
            raise Exception("No access token available. Call authenticate() first.")

        url = f"{self._publication_url}/api/token/EditingApiToken"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
            "User-Agent": "AskDelphi-Python-Client/1.0"
        }

        log_request("GET", url, headers)

        try:
            response = requests.get(url, headers=headers, timeout=30)
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get editing API token: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

        log_response(response)

        if not response.ok:
            error_msg = self._format_error_response(response, "Get editing API token")
            logger.error(error_msg)
            raise Exception(error_msg)

        # Check if we got HTML instead of JSON (indicates wrong URL)
        content_type = response.headers.get('Content-Type', '')
        if 'html' in content_type.lower():
            error_msg = (
                "Received HTML instead of JSON from EditingApiToken endpoint.\n"
                f"  URL: {url}\n"
                f"  Content-Type: {content_type}\n"
                f"  This usually means the publication URL is incorrect.\n"
                f"  The URL should be just the base domain (e.g., https://company.askdelphi.com)\n"
                f"  Current publication URL: {self._publication_url}\n"
                "  Try deleting .askdelphi_tokens.json and authenticating with a fresh portal code."
            )
            logger.error(error_msg)
            raise Exception(error_msg)

        # Parse token (might be a JSON string or plain text)
        try:
            token = response.json()
            if isinstance(token, str):
                pass  # Already a string
            elif isinstance(token, dict):
                token = token.get("token") or token.get("accessToken") or str(token)
        except:
            token = response.text.strip().strip('"')

        logger.info(f"  Received editing API token: {token[:30] if len(token) > 30 else token}...")

        # Validate that the token looks like a JWT
        if not token.startswith("eyJ"):
            error_msg = (
                f"Invalid API token received - does not look like a JWT.\n"
                f"  Token starts with: {token[:50]}...\n"
                f"  Expected: eyJ... (base64 encoded JSON)\n"
                f"  This might indicate the server returned an error page instead of a token.\n"
                f"  Check askdelphi_debug.log for details."
            )
            logger.error(error_msg)
            raise Exception(error_msg)

        # Parse JWT expiry
        try:
            import base64
            payload = token.split(".")[1]
            # Add padding if needed
            payload += "=" * (4 - len(payload) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            self._api_token_expiry = decoded.get("exp", time.time() + 3600)
            logger.debug(f"  Token expires at: {datetime.fromtimestamp(self._api_token_expiry)}")
        except Exception as e:
            logger.warning(f"Could not parse JWT expiry: {e}")
            self._api_token_expiry = time.time() + 3600  # Default 1 hour

        self._api_token = token
        return self._api_token

    def _refresh_tokens(self):
        """Refresh the access token using refresh token."""
        logger.debug("Refreshing tokens...")

        if not self._refresh_token or not self._publication_url:
            raise Exception("No refresh token available")

        url = (
            f"{self._publication_url}/api/token/refresh"
            f"?token={self._access_token}&refreshToken={self._refresh_token}"
        )
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
            "User-Agent": "AskDelphi-Python-Client/1.0"
        }

        log_request("GET", url, headers)

        response = requests.get(url, headers=headers, timeout=30)

        log_response(response)

        if not response.ok:
            raise Exception(f"Failed to refresh token: {response.status_code}")

        data = response.json()
        self._access_token = data.get("token") or data.get("accessToken", self._access_token)
        self._refresh_token = data.get("refresh") or data.get("refreshToken", self._refresh_token)

        self._save_tokens()
        logger.info("Tokens refreshed successfully")

    def _save_tokens(self):
        """Save tokens to cache file."""
        data = {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "publication_url": self._publication_url,
            "saved_at": datetime.now().isoformat()
        }
        try:
            Path(self.token_cache_file).write_text(json.dumps(data, indent=2))
            logger.debug(f"Tokens saved to {self.token_cache_file}")
        except Exception as e:
            logger.warning(f"Could not save tokens: {e}")

    def _load_tokens(self):
        """Load tokens from cache file."""
        try:
            path = Path(self.token_cache_file)
            if path.exists():
                data = json.loads(path.read_text())
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")
                self._publication_url = data.get("publication_url")
                logger.info(f"Loaded cached tokens from {self.token_cache_file}")
                logger.debug(f"  Publication URL: {self._publication_url}")
        except Exception as e:
            logger.debug(f"No cached tokens loaded: {e}")

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
