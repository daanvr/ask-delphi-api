from ask_delphi_api.authentication import AskDelphiClient
from ask_delphi_api.constant import CONSTANTS_DIRECTIE, CONSTANTS_KETEN, CONSTANTS_MIDDEL

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
            # print(item)
            if item['relationTypeName'] == relationTypeName:
                print(f"{item['relationTypeName']} => relationTypeId {item["relationTypeId"]}")
                relationTypeId = item["relationTypeId"]
                break
        
        return relationTypeId
    
    def get_project_tags(self, topicId: str, topicVersionId: str):
        endpoint = f"/v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topicId}/topicVersion/{topicVersionId}/editortagmodel"
        response = self.client._request("GET", endpoint)
        return {item["hierarchyNodeTitle"]: item for item in response['data']['projectTags']}

    def add_tag(self, topic_id : str, topic_version_id : str, tag_data: dict):
        endpoint = f"/v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/topicVersion/{topic_version_id}/tag"
        return self.client._request("POST", endpoint, json_data={"tags": [tag_data]})
    
    def add_tags_to_topic(self, topic_id : str, topic_version_id : str, tags : dict, project_tags : dict):
        for tag in tags:
            print(tag["type"])
            for value in tag["values"]:
                if tag["type"] == "Directie" : value = CONSTANTS_DIRECTIE[value]
                elif tag["type"] == "Keten"  : value = CONSTANTS_KETEN[value]
                elif tag["type"] == "Middel" : value = CONSTANTS_MIDDEL[value]
                tag_data = project_tags[value]
                print(f"{tag_data["hierarchyNodeTitle"]}, {tag_data["hierarchyTopicId"]}")
                self.add_tag(topic_id, topic_version_id, tag_data)

