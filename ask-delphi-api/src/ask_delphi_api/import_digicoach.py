import uuid
from ask_delphi_api.authentication import AskDelphiClient
from ask_delphi_api.project import Project
from ask_delphi_api.topictools import TopicTools
from ask_delphi_api.relation import Relation
from ask_delphi_api.workflow import Workflow

class Import:

    DIGICOACH_NAME = "Digicoach"
    TASK_NAME = "Taak"
    ACTION_NAME = "Stap"

    def __init__(self):

        self.client = AskDelphiClient()
        self.client.authenticate()   # pakt automatisch portal code uit .env
        self.workflow = Workflow(self.client)
        self.project = Project(self.client)
        self.topic = TopicTools(self.client, self.project)
        self.relation = Relation(self.client)

    def _get_topic(self):
        return self.topic
    
    def create_link(self, description: str, topicId: str) -> str:
        target = f"target=\"{topicId}\" use=\"default\" view=\"default\""
        thumbnail= "" 
        link = f"link=\"tenant/{self.client.tenant_id}/project/{self.client.project_id}/acl/{self.client.acl_entry_id}/topic/{topicId}/edit"
        doppio_link = f"<doppio-link {target} title=\"{description}\" {thumbnail} {link}>{description}</doppio-link>"
        return doppio_link
        
    # Create Voorgedefinieerde zoekopdracht topic
    def create_voorgedefinieerde_zoekopdracht_topic(self, name: str) -> str:
        topic_id_predefined_search = self.topic.topic_upload(name, "Pre-defined search")
        topic_version_id_predefined_search = self.topic.get_topicVersionId(topic_id_predefined_search)
        print(f"Created Voorgedefinieerde zoekopdracht topic : {topic_id_predefined_search}")
        return topic_id_predefined_search, topic_version_id_predefined_search

    # Create Digicoach topic
    def create_digicoach(self, name, topic_id_predefined_search, topic_version_id_predefined_search):
        topic_id_digicoach = str(uuid.uuid4())      
        topicTitle = name      
        topicTypeId = self.project.get_topic_type_id("Digitale Coach Procespagina")     
        parentTopicId = topic_id_predefined_search
        parentTopicRelationTypeId = self.relation.get_relation_type_id(topic_id_predefined_search, topic_version_id_predefined_search,"Voorgedefinieerde zoekopdracht")
        parentTopicVersionId = topic_version_id_predefined_search
        self.relation.add_topic_with_relation(topic_id_digicoach, topicTitle, topicTypeId, parentTopicId, parentTopicRelationTypeId, parentTopicVersionId)
        print(f"Created Digicoach topic : {topic_id_digicoach}")
        topic_version_id_digicoach = self.topic.get_topicVersionId(topic_id_digicoach)
        return topic_id_digicoach, topic_version_id_digicoach
    
    # Tag Digitale Coach Procespagina
    def add_tag(self, topic_id_digicoach: str, topic_version_id_digicoach: str, tag: str):
        # self.topic.checkout(topic_id_digicoach)
        self.relation.add_tag(topic_id_digicoach, topic_version_id_digicoach, tag)
        # self.topic.checkin(topic_id_digicoach)

    # Create Task topic
    def create_task(self, name: str, topic_id_digicoach: str, topic_version_id_digicoach: str) -> str:
        topic_id_task = str(uuid.uuid4())
        topicTitle = name      
        topicTypeId = self.project.get_topic_type_id("Task")     
        parentTopicId = topic_id_digicoach
        parentTopicRelationTypeId = self.relation.get_relation_type_id(topic_id_digicoach, topic_version_id_digicoach, "Taak")
        parentTopicVersionId = topic_version_id_digicoach
        self.relation.add_topic_with_relation(topic_id_task, topicTitle, topicTypeId, parentTopicId, parentTopicRelationTypeId, parentTopicVersionId)
        print(f"Created Task topic : {topic_id_task}")
        topic_version_id_task = self.topic.get_topicVersionId(topic_id_task)
        return topic_id_task, topic_version_id_task
    
    # Create Action topic
    def create_step(self, name: str, topic_id_task: str, topic_version_id_task: str) -> str:
        topic_id_step = str(uuid.uuid4())
        topicTitle = name       
        topicTypeId = self.project.get_topic_type_id("Action")     
        parentTopicId = topic_id_task
        parentTopicRelationTypeId = self.relation.get_relation_type_id(topic_id_task, topic_version_id_task, "Stap")
        parentTopicVersionId = topic_version_id_task
        self.relation.add_topic_with_relation(topic_id_step, topicTitle, topicTypeId, parentTopicId, parentTopicRelationTypeId, parentTopicVersionId)
        print(f"Created Action topic : {topic_id_step}")
        topic_version_id_step = self.topic.get_topicVersionId(topic_id_step)
        return topic_id_step, topic_version_id_step
    
    # Create source topic
    def add_source(self, topic_id: str, topic_version_id: str, source: dict) -> str:

        # RelationTypeId uitvragen
        parentTopicId = topic_id
        parentTopicVersionId = topic_version_id
        parentTopicRelationTypeId = self.relation.get_relationTypeId_by_relationTypeName(topic_id, topic_version_id, "Handleidingen en instructies")

        # Creatie source topic
        topic_id_source = str(uuid.uuid4())
        topic_title_source = source["titel"]   
        topic_type_id_source = self.project.get_topic_type_id("External URL")

        # Toevoegen source topic
        self.relation.add_topic_with_relation(topic_id_source, topic_title_source, topic_type_id_source, parentTopicId, parentTopicRelationTypeId, parentTopicVersionId)

        # Update source topic
        topic_version_id_source = self.topic.get_topicVersionId(topic_id_source)
        self.add_link_to_topic(topic_id_source, topic_version_id_source, source["link"])

        return topic_id_source, topic_version_id_source
    
    def add_content_to_topic(self, topicId: str, topicVersionId: str, text: str):
        content = self.topic.get_topic_parts(topicId=topicId)

        # Selecteer part uit topic met daarin de content.
        body_part = None
        groups = content['topicEditorData']['groups']
        for group in groups:
            for part in group['parts']:
                if part["partId"] == "body":
                    body_part = part

        # Pas content topic aan.
        self.topic.topic_add_content(topicVersionId=topicVersionId, topicId=topicId, partId="body", part=body_part, new_text=text)

    def add_link_to_topic(self, topicId: str, topicVersionId: str, url: str):
        content = self.topic.get_topic_parts(topicId=topicId)

        # Selecteer part uit topic met daarin de content.
        body_part = None
        groups = content['topicEditorData']['groups']
        for group in groups:
            for part in group['parts']:
                if part["defaultLabel"] == "Link metadata":
                    body_part = part

        # Pas content topic aan.
        self.topic.topic_add_link(topicVersionId=topicVersionId, topicId=topicId, partId="link-meta-data", part=body_part, new_text=url)


    #  Creates a workflow transition request for predefined_search topic.
    def publiceer(self, topic_id: str):
        request_id = self.workflow.create_workflow_transition_request(topic_id)
        transitions_model = self.workflow.get_workflow_transition_request_transitions_model(request_id)
        self.workflow.update_workflow_transition_request(request_id, transitions_model)
        self.workflow.approve_workflow_transition_request(request_id)