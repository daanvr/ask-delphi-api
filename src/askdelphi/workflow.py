from typing import Dict, Any
from askdelphi.authentication import AskDelphiClient
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
            "Url": "https://digitalecoach.askdelphi.com/cms/tenant/0be6d42b-c278-44e6-888e-ba122840d690/project/397296f6-20dd-45cd-8459-250db2725140/acl/4ecd88f2-979b-4fb0-a95d-175d499bc375"
        }
        result = self.client._request("POST", endpoint, json_data=data)
        result = result.get("response", result)
        request_id = result["workflowTransitionRequestId"]

        return request_id
    
    def get_workflow_transition_request_transitions_model(self, request_id : str) -> str:
        """
        Gets workflow transition request transitions model for specified request id.
        """
        endpoint = f"v1/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/workflow-transition-request/{request_id}/transitions"
        data={}
        result = self.client._request("GET", endpoint, json_data=data)
        result = result.get("response", result)
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
        result = result.get("response", result)
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
        result = result.get("response", result)
        return result
    
   