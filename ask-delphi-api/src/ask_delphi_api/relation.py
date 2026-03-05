from ask_delphi_api.authentication import AskDelphiClient

class Relation:
    def __init__(self, client: AskDelphiClient):
        self.client = client

    def add_relation(self, sourceTopicId: str, sourceTopicVersionId: str, relationTypeId: str, targetTopicId: str):
        """Voeg een relatie toe van dit topic naar andere topics."""
        endpoint = f"v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{sourceTopicId}/topicVersion/{sourceTopicVersionId}/relation"
        return self.client._request(
            "POST",
            endpoint,
            json_data={
                "relationTypeId": relationTypeId,
                "sourceTopicId": sourceTopicId,
                "targetTopicIds": [targetTopicId]
            }
        )

    def add_topic_with_relation(self, topicId: str, topicTitle: str, topicTypeId: str, parentTopicId: str, parentTopicRelationTypeId: str, parentTopicVersionId: str):
        """Voeg een topic met een relatie naar andere topic toe."""
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

    def add_tag(self, topic_id: str, topic_version_id: str, hierarchyNodeTitle: str):
        """Voeg een tag toe aan een topic."""
        tag_data = self.get_tag_data(topic_id, topic_version_id, hierarchyNodeTitle)
        endpoint = f"/v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/topicVersion/{topic_version_id}/tag"
        return self.client._request("POST", endpoint, json_data={"tags": [tag_data]})

    def get_relation_type_id(self, topic_id: str, topicVersionId: str, topicTypeName: str) -> str:
        """Get relation type ID for topicTypeName"""
        task_relation_id = ""
        endpoint = f"/v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/topicVersion/{topicVersionId}/allowedrelations"
        result = self.client._request(
            "GET", 
            endpoint,
            json_data={}
        )
        # result = result.get("response", result)
        for relation in result["topicAllowedRelations"]:
            if relation["topicTypeName"] == topicTypeName:
                relation_type_id = relation["relationTypeId"]
                break

        return relation_type_id
    
    def get_relationTypeId_by_relationTypeName(self, topic_id_action : str, topic_version_id_action: str, relationTypeName: str) -> str:
        endpoint = f"/v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id_action}/topicVersion/{topic_version_id_action}/allowedrelations"
        result = self.client._request(
            "GET", 
            endpoint,
            json_data={}
        )

        relationTypeId = ""
        for item in result["topicAllowedRelations"]:
            print(item)
            if item['relationTypeName'] == relationTypeName:
                print(f"{item['relationTypeName']} => relationTypeId {item["relationTypeId"]}")
                relationTypeId = item["relationTypeId"]
                break
        
        return relationTypeId
    
    def get_tag_data(self, topicId: str, topicVersionId: str, hierarchyNodeTitle: str):
        endpoint = f"/v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topicId}/topicVersion/{topicVersionId}/editortagmodel"
        response = self.client._request("GET", endpoint)
        # response = response.get("response", response)

        tag_data = {}
        for tag in response['data']['projectTags']:
            if tag["hierarchyNodeTitle"].lower() == hierarchyNodeTitle:
                tag_data = tag
                break
        return tag_data
