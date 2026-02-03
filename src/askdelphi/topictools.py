from typing import Optional
from askdelphi.authentication import AskDelphiClient

TOPIC_TYPE_IDS = {
            "Digitale Coach Procespagina": "7d332fbb-44f5-469f-b570-874e701e526b",
            "Stap": "c568af9a-6c89-45cf-a580-bc94e1c62ae3",
            "Taak": "6aba8437-c8df-42d2-a868-840847c124ca"
        }

class TopicTools:
    def __init__(self, client: AskDelphiClient):
        self.client = client

    def topic_upload(self, topicTitle: str, topicTypeName: str):
        topicTypeId = TOPIC_TYPE_IDS.get(topicTypeName)
        
        if topicTypeId is None:
            raise ValueError(
                f"Unknown topic type: '{topicTypeName}'."
                f"Available types: {list(TOPIC_TYPE_IDS.keys())}"
            )
        
        endpoint = "v4/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topic"
        data = {
            "topicTitle": topicTitle,
            "topicTypeId": topicTypeId
            }
        return self.client._request("POST", endpoint, json_data=data)