from typing import Dict, Any
from askdelphi.authentication import AskDelphiClient

class Project:
    def __init__(self, client: AskDelphiClient):
        self.client = client

    # =========================================================================
    # Content Design
    # =========================================================================

    def get_contentdesign(self) -> Dict[str, Any]:
        """
        Get the content design (topic types, relations, etc.) for the project.
        Returns:
            Content design with topicTypes, relations, etc.
        """

        endpoint = "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/contentdesign"
        data = {}
        contentdesign = self.client._request("GET", endpoint, json_data=data)
        contentdesign = contentdesign.get("response", contentdesign)

        return contentdesign
    
    # =========================================================================
    # ContentTopic Types
    # =========================================================================

    def get_topic_types(self) -> dict:
        """ Haalt de beschikbare AskDelphi-topictype IDs op. 
        Returns:        
        dict: Mapping met topictype action, task en digitale coach procespagina"""

        topic_type_map = {}
        contentdesign = self.get_contentdesign()
        topic_types = contentdesign.get("topicTypes", [])

        for i, tt in enumerate(topic_types):
            if tt.get("title").lower() in [
                "action", 
                "task", 
                "digitale coach procespagina", 
                "homepage", 
                "pagina structuur voorgedefinieerde zoekopdracht",
                "pre-defined search"]:
                topic_type_map[tt.get("title")] = tt.get("key")

        return topic_type_map
    
    # =========================================================================
    # ContentTopicType ID
    # =========================================================================

    # TOPIC_TYPE_IDS = {
    #   "Digitale Coach Procespagina": "7d332fbb-44f5-469f-b570-874e701e526b",
    #   "Stap": "c568af9a-6c89-45cf-a580-bc94e1c62ae3",
    #   "Taak": "6aba8437-c8df-42d2-a868-840847c124ca"
    # }

    def get_topic_type_id(self, topicTypeName) -> str:
        """ Haalt de beschikbare AskDelphi-topictype ID op. 
        Returns: topicTypeId """

        topic_type_map = self.get_topic_types()
        topicTypeId = topic_type_map[topicTypeName]

        if topicTypeId is None:
            raise ValueError(
                f"Unknown topic type: '{topicTypeName}'."
                f"Available types: {list(self.project.topic_type_map.keys())}"
            )

        return topicTypeId