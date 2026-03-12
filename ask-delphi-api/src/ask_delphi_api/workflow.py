from typing import Dict, Any
from ask_delphi_api.authentication import AskDelphiClient
from datetime import datetime, timezone

class Workflow:
    def __init__(self, client: AskDelphiClient):
        self.client = client

    def create_workflow_transition_request(self, topic_id : str) -> str:
        """
        Creates a workflow transition request for specifiek topic.
        """
        endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/workflow-transition-request/topic/{topic_id}"
        data={
            "Url": f"https://digitalecoach.askdelphi.com/cms/"
                   f"tenant/{self.client.tenant_id}/"
                   f"project/{self.client.project_id}/"
                   f"acl/{self.client.acl_entry_id}"
        }
        result = self.client._request("POST", endpoint, json_data=data)
        # result = result.get("response", result)
        request_id = result["workflowTransitionRequestId"]

        return request_id
    
    def get_workflow_transition_request_transitions_model(self, request_id : str) -> str:
        """
        Gets workflow transition request transitions model for specified request id.
        """
        endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/workflow-transition-request/{request_id}/transitions"
        data={}
        result = self.client._request("GET", endpoint, json_data=data)
        # result = result.get("response", result)
        return result
    
    def extract_steps(self, transitions_model):
        """
        Extracts 'transitionId' and 'sequenceNo' from input['transitions_model']['selectedTransitions'].
        Returns a sorted list of steps.
        """
        transitions = transitions_model["data"]["selectedTransitions"]
        steps = [
            {
                "transitionId": t["transitionId"],
                "sequenceNo": t["sequenceNo"]
            }
            for t in transitions
        ]

        # Sorteer op sequenceNo (mocht input in willekeurige volgorde staan)
        steps.sort(key=lambda s: s["sequenceNo"])
        return steps
    
    def update_workflow_transition_request(self, request_id : str, transitions_model : Dict) -> str:
        """
        Update_workflow_transition_request for specified request id.
        """

        steps = self.extract_steps(transitions_model)

        endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/workflow-transition-request/{request_id}/transitions"
        data={}
        result = self.client._request("PUT", endpoint, json_data={"data": steps})
        # result = result.get("response", result)
        return result
    
    def approve_workflow_transition_request(self, request_id : str) -> str:
        """
        Approves workflow transition request for specified request id.
        """
        effectiveDate = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        print(effectiveDate)

        endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/workflow-transition-request/{request_id}/approve"
        data={
             "effectiveDate": effectiveDate
        }
        result = self.client._request("POST", endpoint, json_data=data)
        # result = result.get("response", result)
        return result
    
    def get_workflow_id_by_name(self, payload: Any, target_name: str = "Default workflow") -> Optional[str]:
        """
        Zoekt veilig naar het eerste item in payload['data'] met name == target_name.
        Geeft het ID (str) terug of None als niet gevonden of als de structuur afwijkt.
        """

        if not isinstance(payload, dict):
            return None

        items = payload.get('data')
        if not isinstance(items, list) or not items:
            return None

        for item in items:
            if isinstance(item, dict) and item.get('name') == target_name:
                return item.get('id')

        return None

    def extract_stage_ids(self, payload):
        """
        Haalt de stage IDs op voor Concept, Test en Productie.
        Geeft een dict terug: {'Concept': <id>, 'Test': <id>, 'Productie': <id>}
        """

        # De drie stages waar we ID's van willen
        target_titles = {"Concept", "Test", "Productie"}

        result = {title: None for title in target_titles}

        # Veilig navigeren naar de stages
        stages = (
            payload.get("data", {})
                .get("stages", [])
        )

        if not isinstance(stages, list):
            return result  # lege dict, alles None

        # Door de stage-objecten lopen
        for stage in stages:
            if not isinstance(stage, dict):
                continue

            title = stage.get("title")
            stage_id = stage.get("id")

            if title in target_titles:
                result[title] = stage_id

        return result
    
    def get_workflowstate_ids(self):
        workflowstate_ids = {}

        # Ophalen workflow_id
        endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/workflow/search"
        data = {}
        response = self.client._request("POST", endpoint, json_data=data)
        workflow_id = self.get_workflow_id_by_name(response, "Default workflow")

        # Ophalen workflowstate_ids Concept, Test, Productie
        endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/workflow/{workflow_id}"
        data = {}
        response = self.client._request("GET", endpoint, json_data=data)
        workflowstate_ids = self.extract_stage_ids(response)

        return workflowstate_ids
    
       #  Creates a workflow transition request for predefined_search topic.
    def publiceer(self, topic_id: str):
        request_id = self.create_workflow_transition_request(topic_id)
        transitions_model = self.get_workflow_transition_request_transitions_model(request_id)
        self.update_workflow_transition_request(request_id, transitions_model)
        self.approve_workflow_transition_request(request_id)
    
   