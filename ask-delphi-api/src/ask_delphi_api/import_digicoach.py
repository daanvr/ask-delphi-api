import uuid
from typing import List, Dict
import re
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
        self.link_list = {}

    import re

    def is_alleen_url(tekst):    
        patroon = r"""^        
            (https?:\/\/)?                 # optioneel http/https        
            ([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,} # domeinnaam        
            (\/\S*)?                       # optioneel pad    
        $"""
        return re.match(patroon, tekst.strip(), re.VERBOSE) is not None

    def create_source_topics(self, sources):
        topics = self.topic.fetch_topiclist()
        self.upload_source_topics(sources, topics)

    def create_link_list(self, json_digicoach: list[dict], topics: list[dict]):

        bronnen = {}

        tasks = json_digicoach["tasks"]
        for task in tasks:

            topic = self.topic.get_topic_by_title(task["name"], topics)
            bronnen[topic["title"]] = topic["topicGuid"]

            steps = task["steps"]

            for step in steps:
                topic = self.topic.get_topic_by_title(step["name"], topics)
                bronnen[topic["title"]] = topic["topicGuid"]

        sources = json_digicoach["sources"]
        for source in sources:
            topic = self.topic.get_topic_by_title(source["titel"], topics)
            bronnen[topic["title"]] = topic["topicGuid"]
        
        self.link_list = bronnen

    def classify_url(self, url: str) -> str:
        url = url.lower()

        if "www.belastingdienst.nl" in url:             return "External URL"
        elif "connectpeople.belastingdienst.nl" in url: return "ConnectPeople"
        else:                                           return "External URL"

    def upload_source_topics(self, sources: List[Dict], topics: List[Dict]):

        # Opvragen aanwezige topics
        # topics = self.topic.fetch_topiclist()

        # Check source topic beschikbaar en zoniet aanmaken
        for source in sources:
            topic = self.topic.get_topic_by_title(source["titel"], topics)
            if topic is not None:
                print(f"Gevonden : {topic["topicGuid"]}, {topic["title"]}, {topic["topicTypeName"]}, {source["link"]}")
            else:
                topic_type_name = self.classify_url(source["link"])
                topic_id = self.topic.topic_upload(source["titel"], topic_type_name)
                topic_version_id = self.topic.get_topicVersionId(topic_id)
                self.add_link_to_topic(topic_id, topic_version_id, source["link"])
                self.topic.checkin(topic_id)
                self.publiceer(topic_id)

                print(f"Niet gevonden : {source["link"]} toegevoegd")

    def _get_topic(self):
        return self.topic
    
    def create_link(self, description: str, target_topic_id: str) -> str:
        link = f"\xa0<doppio-link " \
            f"target=\"{target_topic_id}\" " \
            f"use=\"default\" " \
            f"view=\"default\" " \
            f"title=\"{description}\" " \
            f"thumbnail=\"\" " \
            f"link=\"tenant/{self.client.tenant_id}/project/{self.client.project_id}/acl/{self.client.acl_entry_id}/topic/{target_topic_id}/edit\">" \
            f"{description}</doppio-link><span>\xa0</span>"
        return link
    
    # sources: Dict[str, str]
    def hyperlink_html(self, description: str) -> str:

        sources = self.link_list

        if not sources:
            return description

        # titels sorteren lang -> kort
        titles = sorted(sources.keys(), key=len, reverse=True)

        # Bouw regex met named groups: (?P<titel>escaped_term)
        parts = []
        for idx, t in enumerate(titles):
            group_name = f"G{idx}"
            parts.append(f"(?P<{group_name}>{re.escape(t)})")

        pattern = re.compile("|".join(parts), re.IGNORECASE)

        def _repl(m: re.Match) -> str:
            matched_text = m.group(0)
            
            # bepaal welke groep gematched is
            for idx, t in enumerate(titles):
                group_name = f"G{idx}"
                if m.group(group_name):
                    topicGuid = sources[t]
                    return self.create_link(matched_text, topicGuid)

            return matched_text  # zou nooit gebeuren

        return pattern.sub(_repl, description)
        
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
    
    def keys_by_value(self, value):    
        return [k for k, v in self.link_list.items() if v == value]

    # Sources (linkjes) toevoegen aan pyramide
    def add_sources(self, topic_id: str, topic_version_id: str, text: str, sources: list[dict]):

        topic_id_links = []

        # Externe linkjes waarvan de titel voorkomt in de text detecteren
        for source in sources:
            # print(f"{source["titel"]}, {source["type"]}, {source["link"]}")
            if source["titel"].lower() in text.lower():
                topic_id_link = self.link_list[source["titel"]]
                topic_id_links.append(topic_id_link)

        # RelationTypeId "Handleidingen en instructies" uitvragen
        # Todo : In eerste instantie de links onder Handleidingen en instructies geplaatst, navraag hoe dit te verbeteren
        relationTypeId = self.relation.get_relationTypeId_by_relationTypeName(topic_id, topic_version_id, "Handleidingen en instructies")

        # Externe links als relatie in de pyramide toevoegen
        for topic_id_link in topic_id_links:
            self.relation.add_relation(topic_id, topic_version_id, relationTypeId, topic_id_link)
            link_title = self.keys_by_value(topic_id_link)
            print(f"Externe link : {link_title} toegevoegd onder Handleidingen en instructies")
    
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

        # Interne en externe links
        text = self.hyperlink_html(text) 

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