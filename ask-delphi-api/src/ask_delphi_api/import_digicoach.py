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

    def __init__(self, client: AskDelphiClient):

        self.client = AskDelphiClient()
        self.client.authenticate()   # pakt automatisch portal code uit .env
        self.workflow = Workflow(self.client)
        self.project = Project(self.client)
        self.topic = TopicTools(self.client, self.project)
        self.relation = Relation(self.client)
        
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
        self.relation.add_topic_with_relation(self.client, topic_id_digicoach, topicTitle, topicTypeId, parentTopicId, parentTopicRelationTypeId, parentTopicVersionId)
        print(f"Created Digicoach topic : {topic_id_digicoach}")
        topic_version_id_digicoach = self.topic.get_topicVersionId(topic_id_digicoach)
        return topic_id_digicoach, topic_version_id_digicoach
    
    # Tag Digitale Coach Procespagina
    # def add_tag():
    #     relation.add_tag(topic_id_digicoach, topic_version_id_digicoach, "interactie")