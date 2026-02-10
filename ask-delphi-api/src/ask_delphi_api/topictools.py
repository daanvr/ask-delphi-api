from typing import Optional
from ask_delphi_api.authentication import AskDelphiClient
from ask_delphi_api.project import Project

class TopicTools:
    def __init__(self, client: AskDelphiClient):
        self.client = client
        self.project = Project(client)

    def topic_upload(self, topicTitle: str, topicTypeName: str):
        topicTypeId = self.project.get_topic_type_id(topicTypeName)
        
        endpoint = "v4/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic"
        data = {
            "topicTitle": topicTitle,
            "topicTypeId": topicTypeId
            }
        
        topic = self.client._request("POST", endpoint, json_data=data)
        
        return topic
    
    def checkin_checkout(self, topicId: str, action: int):
        """
        Check-in (0) of check-out (1) van een topic.
        """

        if action not in (0, 1):
            raise ValueError("action must be 0 (check-in) or 1 (check-out)")
        
        endpoint = f"/v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topicId}/workflowstate"
        data = {
            "action": action
            }
        
        result = self.client._request("POST", endpoint, json_data=data)
        return result
    
    def checkin(self, topicId: str):
        """Voer een check-in uit"""
        return self.checkin_checkout(topicId, 0)
    
    def checkout(self, topicId: str):
        """Voer een check-out uit"""
        return self.checkin_checkout(topicId, 1)
        