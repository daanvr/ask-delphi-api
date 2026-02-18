from typing import Optional, Dict
from ask_delphi_api.authentication import AskDelphiClient
from ask_delphi_api.project import Project
import pprint

class TopicTools:
    
    def __init__(self, client: AskDelphiClient, project: Project):
        self.client = client
        self.project = project

    def get_topic_parts(self, topicId: str):
        """Haal alle parts op van topic met topicId."""
        endpoint = f"/v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topicId}/part"
        data = {}
        topic = self.client._request("GET", endpoint, json_data=data)
        return topic
    
    def topic_add_content(self, topicVersionId: str, topicId: str, partId: str, part: Dict, new_text: str):
        """Voeg content toe aan topic met topicId."""
        endpoint = f"/v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topicId}/topicVersion/{topicVersionId}/part/{partId}"
        part['editors'][0]['value']['richTextEditor'] = {'value': new_text }
        json_data = {"part": part}
        topic = self.client._request("PUT", endpoint, json_data=json_data)
        return topic
    
    def topic_add_link(self, topicVersionId: str, topicId: str, partId: str, part: Dict, new_text: str):
        """Voeg contentlink toe aan topic met topicId."""
        endpoint = f"/v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topicId}/topicVersion/{topicVersionId}/part/{partId}"
        part['editors'][0]['value']['string'] = {'markup': None, 'value': new_text }
        json_data = {"part": part}
        topic = self.client._request("PUT", endpoint, json_data=json_data)
        return topic

    def topic_upload(self, topicTitle: str, topicTypeName: str):
        """Voeg een topic toe van meegegeven topictype naam."""
        topicTypeId = self.project.get_topic_type_id(topicTypeName)
        endpoint = "v4/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic"
        data = {
            "topicTitle": topicTitle,
            "topicTypeId": topicTypeId
            }
        topic = self.client._request("POST", endpoint, json_data=data)
        return topic["topicId"]
    
    def delete_topic(self, topicId: str, topicVersionId: str):
        """Verwijder een topic."""
        endpoint = f"v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topicId}/topicVersion/{topicVersionId}"
        data = {
            "workflowActions": {}
        }
        return self.client._request("DELETE", endpoint, json_data=data)
    
    def get_topicVersionId(self, topicId) -> str:
        endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topicId}/workflowstate"
        data={
            "action": 1
        }
        result = self.client._request("POST", endpoint, json_data=data)
        return result["topicVersionId"]
    
    def checkin_checkout(self, topicId: str, action: int):
        """
        Check-in (0) of check-out (1) van een topic.
        """

        if action not in (0, 1):
            raise ValueError("action must be 0 (check-in) or 1 (check-out)")
        
        endpoint = f"/v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topicId}/workflowstate"
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
