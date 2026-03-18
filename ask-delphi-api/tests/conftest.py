"""
Gedeelde test fixtures.
"""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_client():
    """Mock AskDelphiClient met vaste IDs."""
    client = MagicMock()
    client.tenant_id = "tenant-111"
    client.project_id = "project-222"
    client.acl_entry_id = "acl-333"
    client._request = MagicMock(return_value={})
    return client
