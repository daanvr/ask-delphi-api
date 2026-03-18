"""
Tests voor config.py — topic type lookup.
"""
import pytest
from unittest.mock import patch
from ask_delphi_api.config import get_topic_type_id, get_topic_types


@patch("ask_delphi_api.config.api")
def test_get_topic_types(mock_api, mock_client):
    mock_api.get_content_design.return_value = {
        "topicTypes": [
            {"title": "Task", "key": "task-key-1"},
            {"title": "Action", "key": "action-key-1"},
        ]
    }
    result = get_topic_types(mock_client)
    assert result == {"Task": "task-key-1", "Action": "action-key-1"}


@patch("ask_delphi_api.config.api")
def test_get_topic_type_id_found(mock_api, mock_client):
    mock_api.get_content_design.return_value = {
        "topicTypes": [
            {"title": "Task", "key": "task-key-1"},
        ]
    }
    assert get_topic_type_id(mock_client, "Task") == "task-key-1"


@patch("ask_delphi_api.config.api")
def test_get_topic_type_id_not_found(mock_api, mock_client):
    mock_api.get_content_design.return_value = {
        "topicTypes": [
            {"title": "Task", "key": "task-key-1"},
        ]
    }
    with pytest.raises(ValueError):
        get_topic_type_id(mock_client, "Onbekend")
