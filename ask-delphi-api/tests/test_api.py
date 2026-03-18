"""
Tests voor api.py — verifieert dat elke functie exact de juiste
method, endpoint en data doorstuurt naar client._request().

Dit is de kern-test: als deze slaagt na refactoring, zijn de API calls identiek gebleven.
"""
from ask_delphi_api import api


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------

def test_get_topic_relations(mock_client):
    api.get_topic_relations(mock_client, "TOPIC-1")
    mock_client._request.assert_called_once_with(
        "GET",
        "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic/TOPIC-1/relation",
        json_data={}
    )


def test_get_topic_parts(mock_client):
    api.get_topic_parts(mock_client, "TOPIC-1")
    mock_client._request.assert_called_once_with(
        "GET",
        "/v3/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic/TOPIC-1/part",
        json_data={}
    )


def test_update_topic_part(mock_client):
    part_data = {"editors": [{"value": {}}]}
    api.update_topic_part(mock_client, "T1", "TV1", "body", part_data)
    mock_client._request.assert_called_once_with(
        "PUT",
        "/v2/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic/T1/topicVersion/TV1/part/body",
        json_data={"part": part_data}
    )


def test_create_topic_simple(mock_client):
    topic_data = {"topicTitle": "Test Topic", "topicTypeId": "TYPE-1"}
    api.create_topic(mock_client, topic_data)
    mock_client._request.assert_called_once_with(
        "POST",
        "v4/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic",
        json_data=topic_data
    )


def test_create_topic_with_relation(mock_client):
    topic_data = {
        "topicId": "NEW-1",
        "topicTitle": "Test",
        "topicTypeId": "TYPE-1",
        "parentTopicId": "PARENT-1",
        "parentTopicRelationTypeId": "REL-1",
        "parentTopicVersionId": "PV-1"
    }
    api.create_topic(mock_client, topic_data)
    mock_client._request.assert_called_once_with(
        "POST",
        "v4/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic",
        json_data=topic_data
    )


def test_delete_topic(mock_client):
    workflow_data = {
        "workflowActions": {
            "applyWorkflowStageIds": ["s1", "s2"],
            "increaseMajorVersionNo": True
        }
    }
    api.delete_topic(mock_client, "T1", "TV1", workflow_data)
    mock_client._request.assert_called_once_with(
        "DELETE",
        "v3/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic/T1/topicVersion/TV1",
        json_data=workflow_data
    )


def test_post_topic_workflowstate(mock_client):
    api.post_topic_workflowstate(mock_client, "T1", 1)
    mock_client._request.assert_called_once_with(
        "POST",
        "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic/T1/workflowstate",
        json_data={"action": 1}
    )


def test_post_topic_workflowstate_v3(mock_client):
    api.post_topic_workflowstate_v3(mock_client, "T1", 0)
    mock_client._request.assert_called_once_with(
        "POST",
        "/v3/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic/T1/workflowstate",
        json_data={"action": 0}
    )


def test_post_topiclist(mock_client):
    api.post_topiclist(mock_client, query="", page=0, page_size=100)
    mock_client._request.assert_called_once_with(
        "POST",
        "/v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topiclist",
        json_data={"query": "", "page": 0, "pageSize": 100}
    )


# ---------------------------------------------------------------------------
# Relations
# ---------------------------------------------------------------------------

def test_delete_topic_relation(mock_client):
    api.delete_topic_relation(mock_client, "S1", "SV1", "T1", "REL-1")
    mock_client._request.assert_called_once_with(
        "POST",
        "v2/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic/S1/topicVersion/SV1/relation/delete",
        json_data={
            "relationTypeId": "REL-1",
            "sourceTopicId": "S1",
            "targetTopicId": "T1",
        }
    )


def test_add_topic_relation(mock_client):
    api.add_topic_relation(mock_client, "S1", "SV1", "REL-1", ["T1"])
    mock_client._request.assert_called_once_with(
        "POST",
        "v2/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic/S1/topicVersion/SV1/relation",
        json_data={
            "relationTypeId": "REL-1",
            "sourceTopicId": "S1",
            "targetTopicIds": ["T1"]
        }
    )


def test_add_topic_relation_single_id(mock_client):
    """Wanneer target_topic_ids een string is, wrap in list."""
    api.add_topic_relation(mock_client, "S1", "SV1", "REL-1", "T1")
    mock_client._request.assert_called_once_with(
        "POST",
        "v2/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic/S1/topicVersion/SV1/relation",
        json_data={
            "relationTypeId": "REL-1",
            "sourceTopicId": "S1",
            "targetTopicIds": ["T1"]
        }
    )


def test_get_allowed_relations(mock_client):
    api.get_allowed_relations(mock_client, "T1", "TV1")
    mock_client._request.assert_called_once_with(
        "GET",
        "/v2/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic/T1/topicVersion/TV1/allowedrelations",
        json_data={}
    )


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def test_get_editor_tag_model(mock_client):
    api.get_editor_tag_model(mock_client, "T1", "TV1")
    mock_client._request.assert_called_once_with(
        "GET",
        "/v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic/T1/topicVersion/TV1/editortagmodel",
    )


def test_add_topic_tag(mock_client):
    tag_data = {"hierarchyNodeTitle": "Test Tag", "hierarchyTopicId": "HT-1"}
    api.add_topic_tag(mock_client, "T1", "TV1", tag_data)
    mock_client._request.assert_called_once_with(
        "POST",
        "/v2/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic/T1/topicVersion/TV1/tag",
        json_data={"tags": [tag_data]}
    )


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

def test_create_workflow_transition_request(mock_client):
    api.create_workflow_transition_request(mock_client, "T1", "https://example.com")
    mock_client._request.assert_called_once_with(
        "POST",
        "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/workflow-transition-request/topic/T1",
        json_data={"Url": "https://example.com"}
    )


def test_get_workflow_transitions(mock_client):
    api.get_workflow_transitions(mock_client, "REQ-1")
    mock_client._request.assert_called_once_with(
        "GET",
        "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/workflow-transition-request/REQ-1/transitions",
        json_data={}
    )


def test_update_workflow_transitions(mock_client):
    steps = [{"transitionId": "TR-1", "sequenceNo": 1}]
    api.update_workflow_transitions(mock_client, "REQ-1", steps)
    mock_client._request.assert_called_once_with(
        "PUT",
        "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/workflow-transition-request/REQ-1/transitions",
        json_data={"data": steps}
    )


def test_approve_workflow_transition_request(mock_client):
    api.approve_workflow_transition_request(mock_client, "REQ-1", "2024-01-01T00:00:00Z")
    mock_client._request.assert_called_once_with(
        "POST",
        "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/workflow-transition-request/REQ-1/approve",
        json_data={"effectiveDate": "2024-01-01T00:00:00Z"}
    )


def test_search_workflows(mock_client):
    api.search_workflows(mock_client)
    mock_client._request.assert_called_once_with(
        "POST",
        "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/workflow/search",
        json_data={}
    )


def test_get_workflow(mock_client):
    api.get_workflow(mock_client, "WF-1")
    mock_client._request.assert_called_once_with(
        "GET",
        "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/workflow/WF-1",
        json_data={}
    )


# ---------------------------------------------------------------------------
# Project / Content Design
# ---------------------------------------------------------------------------

def test_get_content_design(mock_client):
    api.get_content_design(mock_client)
    mock_client._request.assert_called_once_with(
        "GET",
        "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/contentdesign",
        json_data={}
    )


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

def test_upload_resource(mock_client):
    files = {"File": ("test.png", b"data", "image/png")}
    api.upload_resource(mock_client, files)
    mock_client._request.assert_called_once_with(
        "POST",
        "/v2/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/resource",
        files=files
    )
