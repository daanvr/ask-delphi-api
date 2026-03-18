"""
Workflow: publiceren en workflow state management.
"""
from typing import Optional, Any
from datetime import datetime, timezone
from ask_delphi_api import api


def extract_steps(transitions_model):
    """Extract transitionId en sequenceNo uit transitions_model. Gesorteerd op sequenceNo."""
    transitions = transitions_model["data"]["selectedTransitions"]
    steps = [
        {
            "transitionId": t["transitionId"],
            "sequenceNo": t["sequenceNo"]
        }
        for t in transitions
    ]
    steps.sort(key=lambda s: s["sequenceNo"])
    return steps


def get_workflow_id_by_name(payload, target_name="Default workflow"):
    """Zoek workflow ID op naam in payload['data']."""
    if not isinstance(payload, dict):
        return None
    items = payload.get('data')
    if not isinstance(items, list) or not items:
        return None
    for item in items:
        if isinstance(item, dict) and item.get('name') == target_name:
            return item.get('id')
    return None


def extract_stage_ids(payload):
    """Haal stage IDs op voor Concept, Test en Productie."""
    target_titles = {"Concept", "Test", "Productie"}
    result = {title: None for title in target_titles}

    stages = payload.get("data", {}).get("stages", [])
    if not isinstance(stages, list):
        return result

    for stage in stages:
        if not isinstance(stage, dict):
            continue
        title = stage.get("title")
        stage_id = stage.get("id")
        if title in target_titles:
            result[title] = stage_id

    return result


def get_workflowstate_ids(client):
    """Haal workflowstate IDs op voor Concept, Test en Productie."""
    response = api.search_workflows(client)
    workflow_id = get_workflow_id_by_name(response, "Default workflow")

    response = api.get_workflow(client, workflow_id)
    return extract_stage_ids(response)


def publiceer(client, topic_id):
    """Publiceer een topic via het workflow transition proces."""
    url = (
        f"https://digitalecoach.askdelphi.com/cms/"
        f"tenant/{client.tenant_id}/"
        f"project/{client.project_id}/"
        f"acl/{client.acl_entry_id}"
    )
    result = api.create_workflow_transition_request(client, topic_id, url)
    request_id = result["workflowTransitionRequestId"]

    transitions_model = api.get_workflow_transitions(client, request_id)

    steps = extract_steps(transitions_model)
    api.update_workflow_transitions(client, request_id, steps)

    effective_date = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    print(effective_date)
    api.approve_workflow_transition_request(client, request_id, effective_date)
