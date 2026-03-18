"""
Alle AskDelphi API endpoint calls geconsolideerd.

Elke functie doet exact één client._request() call en returnt het ruwe resultaat.
Geen business logic — alleen endpoint, method en payload.
"""


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------

def get_topic_relations(client, topic_id):
    """Opvragen topic relations."""
    endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/relation"
    return client._request("GET", endpoint, json_data={})


def get_topic_parts(client, topic_id):
    """Haal alle parts op van een topic."""
    endpoint = f"/v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/part"
    return client._request("GET", endpoint, json_data={})


def update_topic_part(client, topic_id, topic_version_id, part_id, part_data):
    """Update een part van een topic (content of link)."""
    endpoint = f"/v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/topicVersion/{topic_version_id}/part/{part_id}"
    return client._request("PUT", endpoint, json_data={"part": part_data})


def create_topic(client, topic_data):
    """Maak een nieuw topic aan. topic_data kan simpel (topicTitle+topicTypeId) of met relatie zijn."""
    endpoint = "v4/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic"
    return client._request("POST", endpoint, json_data=topic_data)


def delete_topic(client, topic_id, version_id, workflow_data):
    """Verwijder een topic."""
    endpoint = (
        f"v3/tenant/{{tenantId}}/project/{{projectId}}/"
        f"acl/{{aclEntryId}}/topic/{topic_id}/topicVersion/{version_id}"
    )
    return client._request("DELETE", endpoint, json_data=workflow_data)


def post_topic_workflowstate(client, topic_id, action):
    """Post workflowstate (v1) — gebruikt voor get_topicVersionId."""
    endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/workflowstate"
    return client._request("POST", endpoint, json_data={"action": action})


def post_topic_workflowstate_v3(client, topic_id, action):
    """Post workflowstate (v3) — gebruikt voor checkin/checkout."""
    endpoint = f"/v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/workflowstate"
    return client._request("POST", endpoint, json_data={"action": action})


def post_topiclist(client, query="", page=0, page_size=100):
    """Haal een pagina van de topiclist op."""
    endpoint = "/v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topiclist"
    return client._request("POST", endpoint, json_data={
        "query": query,
        "page": page,
        "pageSize": page_size
    })


# ---------------------------------------------------------------------------
# Relations
# ---------------------------------------------------------------------------

def delete_topic_relation(client, source_id, source_version_id, target_id, relation_type_id):
    """Verwijder een topic-relatie."""
    endpoint = (
        f"v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}"
        f"/topic/{source_id}/topicVersion/{source_version_id}/relation/delete"
    )
    return client._request("POST", endpoint, json_data={
        "relationTypeId": relation_type_id,
        "sourceTopicId": source_id,
        "targetTopicId": target_id,
    })


def add_topic_relation(client, source_id, source_version_id, relation_type_id, target_topic_ids):
    """Voeg een relatie toe van source naar target topics."""
    endpoint = f"v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{source_id}/topicVersion/{source_version_id}/relation"
    return client._request("POST", endpoint, json_data={
        "relationTypeId": relation_type_id,
        "sourceTopicId": source_id,
        "targetTopicIds": target_topic_ids if isinstance(target_topic_ids, list) else [target_topic_ids]
    })


def get_allowed_relations(client, topic_id, topic_version_id):
    """Haal toegestane relaties op voor een topic."""
    endpoint = f"/v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/topicVersion/{topic_version_id}/allowedrelations"
    return client._request("GET", endpoint, json_data={})


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def get_editor_tag_model(client, topic_id, topic_version_id):
    """Haal de editor tag model op."""
    endpoint = f"/v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/topicVersion/{topic_version_id}/editortagmodel"
    return client._request("GET", endpoint)


def add_topic_tag(client, topic_id, topic_version_id, tag_data):
    """Voeg een tag toe aan een topic."""
    endpoint = f"/v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/topicVersion/{topic_version_id}/tag"
    return client._request("POST", endpoint, json_data={"tags": [tag_data]})


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

def create_workflow_transition_request(client, topic_id, url):
    """Maak een workflow transition request aan."""
    endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/workflow-transition-request/topic/{topic_id}"
    return client._request("POST", endpoint, json_data={"Url": url})


def get_workflow_transitions(client, request_id):
    """Haal transitions op voor een workflow request."""
    endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/workflow-transition-request/{request_id}/transitions"
    return client._request("GET", endpoint, json_data={})


def update_workflow_transitions(client, request_id, steps):
    """Update transitions voor een workflow request."""
    endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/workflow-transition-request/{request_id}/transitions"
    return client._request("PUT", endpoint, json_data={"data": steps})


def approve_workflow_transition_request(client, request_id, effective_date):
    """Keur een workflow transition request goed."""
    endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/workflow-transition-request/{request_id}/approve"
    return client._request("POST", endpoint, json_data={"effectiveDate": effective_date})


def search_workflows(client):
    """Zoek workflows."""
    endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/workflow/search"
    return client._request("POST", endpoint, json_data={})


def get_workflow(client, workflow_id):
    """Haal een specifieke workflow op."""
    endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/workflow/{workflow_id}"
    return client._request("GET", endpoint, json_data={})


# ---------------------------------------------------------------------------
# Project / Content Design
# ---------------------------------------------------------------------------

def get_content_design(client):
    """Haal het content design (topic types, relations, etc.) op."""
    endpoint = "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/contentdesign"
    return client._request("GET", endpoint, json_data={})


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

def upload_resource(client, files):
    """Upload een resource (bijv. afbeelding)."""
    endpoint = "/v2/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/resource"
    return client._request("POST", endpoint, files=files)
