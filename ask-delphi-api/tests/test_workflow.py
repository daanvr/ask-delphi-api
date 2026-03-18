"""
Tests voor workflow.py — pure logic + API call orchestratie.
"""
from unittest.mock import patch, call
from ask_delphi_api.workflow import (
    extract_steps,
    get_workflow_id_by_name,
    extract_stage_ids,
    publiceer,
)


# ---------------------------------------------------------------------------
# extract_steps (pure logic)
# ---------------------------------------------------------------------------

def test_extract_steps():
    model = {
        "data": {
            "selectedTransitions": [
                {"transitionId": "t2", "sequenceNo": 2, "extra": "ignored"},
                {"transitionId": "t1", "sequenceNo": 1, "extra": "ignored"},
            ]
        }
    }
    result = extract_steps(model)
    assert result == [
        {"transitionId": "t1", "sequenceNo": 1},
        {"transitionId": "t2", "sequenceNo": 2},
    ]


# ---------------------------------------------------------------------------
# get_workflow_id_by_name (pure logic)
# ---------------------------------------------------------------------------

def test_get_workflow_id_by_name_found():
    payload = {"data": [{"name": "Default workflow", "id": "wf-1"}]}
    assert get_workflow_id_by_name(payload) == "wf-1"


def test_get_workflow_id_by_name_not_found():
    payload = {"data": [{"name": "Other", "id": "wf-2"}]}
    assert get_workflow_id_by_name(payload) is None


def test_get_workflow_id_by_name_invalid():
    assert get_workflow_id_by_name("not a dict") is None
    assert get_workflow_id_by_name({"data": []}) is None
    assert get_workflow_id_by_name({}) is None


# ---------------------------------------------------------------------------
# extract_stage_ids (pure logic)
# ---------------------------------------------------------------------------

def test_extract_stage_ids():
    payload = {
        "data": {
            "stages": [
                {"title": "Concept", "id": "c1"},
                {"title": "Test", "id": "t1"},
                {"title": "Productie", "id": "p1"},
                {"title": "Archief", "id": "a1"},
            ]
        }
    }
    result = extract_stage_ids(payload)
    assert result == {"Concept": "c1", "Test": "t1", "Productie": "p1"}


def test_extract_stage_ids_missing():
    payload = {"data": {"stages": [{"title": "Concept", "id": "c1"}]}}
    result = extract_stage_ids(payload)
    assert result["Concept"] == "c1"
    assert result["Test"] is None


# ---------------------------------------------------------------------------
# publiceer (orchestratie — verifieert API call volgorde)
# ---------------------------------------------------------------------------

@patch("ask_delphi_api.workflow.api")
def test_publiceer_api_calls(mock_api, mock_client):
    """Verifieer dat publiceer exact de juiste API calls maakt in de juiste volgorde."""
    mock_api.create_workflow_transition_request.return_value = {
        "workflowTransitionRequestId": "REQ-1"
    }
    mock_api.get_workflow_transitions.return_value = {
        "data": {
            "selectedTransitions": [
                {"transitionId": "tr-1", "sequenceNo": 1},
            ]
        }
    }
    mock_api.update_workflow_transitions.return_value = {}
    mock_api.approve_workflow_transition_request.return_value = {}

    publiceer(mock_client, "TOPIC-1")

    # Verifieer de volgorde
    expected_url = (
        "https://digitalecoach.askdelphi.com/cms/"
        "tenant/tenant-111/"
        "project/project-222/"
        "acl/acl-333"
    )
    mock_api.create_workflow_transition_request.assert_called_once_with(
        mock_client, "TOPIC-1", expected_url
    )
    mock_api.get_workflow_transitions.assert_called_once_with(mock_client, "REQ-1")
    mock_api.update_workflow_transitions.assert_called_once_with(
        mock_client, "REQ-1", [{"transitionId": "tr-1", "sequenceNo": 1}]
    )
    mock_api.approve_workflow_transition_request.assert_called_once()
