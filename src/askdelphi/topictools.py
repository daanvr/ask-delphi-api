from typing import Optional
from askdelphi.authentication import AskDelphiClient

class TopicTools:
    def __init__(self, client: AskDelphiClient):
        self.client = client

    def topic_upload(self, topicTitle: str, topicTypeName: str):
        if topicTypeName == "Digitale Coach Procespagina":
            topicTypeId = "7d332fbb-44f5-469f-b570-874e701e526b"
        else:
            raise ValueError(f"Unknown topic type: {topicTypeName}")
        
        endpoint = "v4/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic"
        data = {
            "topicTitle": topicTitle,
            "topicTypeId": topicTypeId
            }
        return self.client._request("POST", endpoint, json_data=data)