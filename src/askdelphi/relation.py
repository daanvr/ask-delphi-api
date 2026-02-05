from askdelphi.authentication import AskDelphiClient

class Relation:
    def __init__(self, client: AskDelphiClient):
        self.client = client

    def add_relation(self, topic_id: str, topic_version_id: str, relation_type_id: str, target_topic_ids: list):
        """Voeg een relatie toe van dit topic naar andere topics."""
        endpoint = "v2/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic/{topic_id}/topicVersion/{topic_version_id}/relation"
        return self.client._request(
            endpoint,
            json={
                "relationTypeId": [3],
                "sourceTopicId": topic_id,
                "targetTopicIds": target_topic_ids,
            }
        )

    def add_topic_with_relation(self, client: AskDelphiClient, topicId: str, topicTitle: str, topicTypeId: str, parentTopicId: str, parentTopicRelationTypeId: str, parentTopicVersionId: str):
        """Voeg een topic met een relatie naar andere topic toe.  
        Args:        
        - topicId (str): ID van het doel-topic.        
        - topicTitle (str): Titel van het doel-topic.        
        - topicTypeId (str): ID van het topictype.        
        - parentTopicId (str): ID van het bron-topic.
        - parentTopicRelationTypeId (str): ID van het relatietype.        
        - parentTopicVersionId (str): Versie-ID van het bron-topic."""
        endpoint = "v4/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic"
        return self.client._request(
            "POST",
            endpoint,
            json_data={
                "topicId": topicId,
                "topicTitle": topicTitle,
                "topicTypeId": topicTypeId,
                "parentTopicId": parentTopicId,
                "parentTopicRelationTypeId": parentTopicRelationTypeId,
                "parentTopicVersionId": parentTopicVersionId
            }
        )

    def add_tag(self, topic_id: str, topic_version_id: str, hierarchy_topic_id: str, hierarchy_node_id: str):
        """Voeg een tag toe aan een topic."""
        endpoint = f"v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/topicVersion/{topic_version_id}/tag"
        return self.client._request(
            endpoint,
            json={
                "tags": [
                    {
                        "hierarchyTopicId": hierarchy_topic_id,
                        "hierarchyNodeId": hierarchy_node_id,
                    }
                ]
            },
        )

    def get_task_relation_id(self, topic_id: str, topicVersionId: str) -> str:
        """Get relationship ID for task"""
        task_relation_id = ""
        endpoint = f"/v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/topicVersion/{topicVersionId}/allowedrelations"
        result = self.client._request(
            "GET", 
            endpoint,
            json_data={}
        )
        result = result.get("response", result)
        for relation in result["topicAllowedRelations"]:
            if relation["topicTypeName"] == "Taak":
                task_relation_id = relation["relationTypeId"]
                break

        return task_relation_id
