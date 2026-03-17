import re
from typing import List, Dict
import pprint
from typing import Optional, Dict
from datetime import datetime
from ask_delphi_api.authentication import AskDelphiClient
from ask_delphi_api.project import Project

class TopicTools:
    
    def __init__(self, client: AskDelphiClient, project: Project):
        self.client = client
        self.project = project

    def get_topic_relation(self, topicId: str):
        """Opvragen topic relations."""
        endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topicId}/relation"
        data = {}
        return self.client._request("GET", endpoint, json_data=data)

    def get_topic_by_title(self, title: str, topics: List[Dict]):
        # Alle topics met dezelfde title filteren
        matching = [t for t in topics if t.get("title") == title]
        if not matching:
            return None
        # Nieuwste bepalen op basis van lastModificationDate
        topic = max(matching, key=lambda t: t.get("lastModificationDate"))
        return topic

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
    
    def delete_topic(self, topic_id: str, version_id: str, workflowstage_ids: list):
        """Voert de DELETE-call uit voor een topic."""
        endpoint = (
            f"v3/tenant/{{tenantId}}/project/{{projectId}}/"
            f"acl/{{aclEntryId}}/topic/{topic_id}/topicVersion/{version_id}"
        )
        data = {"workflowActions": {
            "applyWorkflowStageIds": workflowstage_ids,
            "increaseMajorVersionNo": True}
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
    
    def parse_iso_ts(self, s: Optional[str]):
        """
        Maakt alle timestamp formaten netjes leesbaar
        """
        if not s:
            return None
        s = s.replace("Z", "")
        if "+" in s:
            s = s.split("+", 1)[0]
        try:
            return datetime.fromisoformat(s)
        except:
            return None
        
    def fetch_topiclist(self, page_size=100):
        """
        Haalt de gegevens van alle topics op. Stopt wanneer een pagina geen resultaten meer bevat. 
        Retourneert een list van topic dicts.
        """
        endpoint = "/v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topiclist"
        all_topics = []
        page = 0

        while True:
            body = {"query": "", 
                    "page": page, 
                    "pageSize": page_size
            }
            resp = self.client._request("POST", endpoint, json_data=body)

            topic_list = resp.get("topicList", {})
            if topic_list:
                items = topic_list.get("result", [])
            else:
                items = resp.get("items", resp.get("data", []))

            if not items:
                break

            all_topics.extend(items)
            page += 1
            
        return all_topics

    def filter_between(self, start_str: str, end_str: str):
        """
        Filteren op basis van timestamp
        """
        start = datetime.fromisoformat(start_str.replace("Z", ""))
        end = datetime.fromisoformat(end_str.replace("Z", ""))

        topics = self.fetch_topiclist()

        selected = []
        for t in topics:
            ts_str = t.get("lastModificationDate")
            ts = self.parse_iso_ts(ts_str)
            if not ts:
                continue

            if start <= ts <= end:
                selected.append({
                    "topicGuid": t.get("topicGuid"),
                    "title": t.get("title"),
                    "LastModificationDate": ts_str
                })

        selected.sort(key=lambda x: self.parse_iso_ts(x["LastModificationDate"]))
        return selected
