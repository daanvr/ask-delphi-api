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
        
        return topic["response"]["topicId"]
        