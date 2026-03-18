"""
Tests voor topic.py — business logic + API call verificatie.
"""
from unittest.mock import patch, MagicMock
from ask_delphi_api.topic import (
    get_topic_by_title,
    fetch_topiclist,
    get_topic_version_id,
    upload_topic,
)


# ---------------------------------------------------------------------------
# get_topic_by_title (pure logic)
# ---------------------------------------------------------------------------

def test_get_topic_by_title_found():
    topics = [
        {"title": "A", "lastModificationDate": "2024-01-01"},
        {"title": "B", "lastModificationDate": "2024-01-02"},
        {"title": "A", "lastModificationDate": "2024-01-03"},
    ]
    result = get_topic_by_title("A", topics)
    assert result["lastModificationDate"] == "2024-01-03"


def test_get_topic_by_title_not_found():
    topics = [{"title": "A", "lastModificationDate": "2024-01-01"}]
    assert get_topic_by_title("B", topics) is None


# ---------------------------------------------------------------------------
# fetch_topiclist (paginatie)
# ---------------------------------------------------------------------------

@patch("ask_delphi_api.topic.api")
def test_fetch_topiclist_pagination(mock_api, mock_client):
    """Verifieer dat fetch_topiclist pagineert tot een lege pagina."""
    mock_api.post_topiclist.side_effect = [
        {"topicList": {"result": [{"title": "A"}, {"title": "B"}]}},
        {"topicList": {"result": [{"title": "C"}]}},
        {"topicList": {"result": []}},
    ]
    result = fetch_topiclist(mock_client, page_size=2)
    assert len(result) == 3
    assert mock_api.post_topiclist.call_count == 3


# ---------------------------------------------------------------------------
# get_topic_version_id
# ---------------------------------------------------------------------------

@patch("ask_delphi_api.topic.api")
def test_get_topic_version_id(mock_api, mock_client):
    mock_api.post_topic_workflowstate.return_value = {"topicVersionId": "TV-1"}
    result = get_topic_version_id(mock_client, "T-1")
    assert result == "TV-1"
    mock_api.post_topic_workflowstate.assert_called_once_with(mock_client, "T-1", 1)


# ---------------------------------------------------------------------------
# upload_topic
# ---------------------------------------------------------------------------

@patch("ask_delphi_api.topic.api")
@patch("ask_delphi_api.topic.config")
def test_upload_topic(mock_config, mock_api, mock_client):
    mock_config.get_topic_type_id.return_value = "TYPE-1"
    mock_api.create_topic.return_value = {"topicId": "NEW-1"}

    result = upload_topic(mock_client, "Mijn Topic", "Task")

    assert result == "NEW-1"
    mock_config.get_topic_type_id.assert_called_once_with(mock_client, "Task")
    mock_api.create_topic.assert_called_once_with(mock_client, {
        "topicTitle": "Mijn Topic",
        "topicTypeId": "TYPE-1"
    })
