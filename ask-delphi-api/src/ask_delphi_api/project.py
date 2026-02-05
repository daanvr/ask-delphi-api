from typing import Dict, Any
from ask_delphi_api.authentication import AskDelphiClient

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
            topic_type_map[tt.get("title")] = tt.get("key")

        return topic_type_map
    
    # =========================================================================
    # ContentTopicType ID
    # =========================================================================

    def get_topic_type_id(self, topicTypeName) -> str:
        """ Haalt de beschikbare AskDelphi-topictype ID op. 
        Returns: topicTypeId """

        topic_type_map = self.get_topic_types()

        topicTypeId = topic_type_map.get(topicTypeName)

        if topicTypeId is None:
            raise ValueError(
                f"Unknown topic type: {topicTypeName}",
                f"Available types: {list(topic_type_map.keys())}")

        return topicTypeId