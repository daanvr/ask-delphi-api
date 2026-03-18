"""
Importer: nieuw opbouwen van een digicoach structuur.

Processtappen (zie post-its):
1. Bronnen aanmaken (intern/extern)
2. Voorgedefinieerde zoekopdracht
3. Proces pagina — tags, content, relatie naar zoekopdracht
4. Aanmaken alle taken — tag, bronnen, relatie naar proces pagina
5. Aanmaken stappen — tag, bronnen
6. Content toevoegen aan taken + stappen — huisstijl, plaatjes, interne verwijzingen, externe verwijzingen
7. Bronnen die niet gebruikt zijn verwijderen
"""
import uuid

from ask_delphi_api.client import AskDelphiClient
from ask_delphi_api import api, topic, topic_content, relations, workflow, config
from ask_delphi_api.helpers import classify_url, hyperlink_html, create_link, keys_by_value


class Import:

    DIGICOACH_NAME = "Digicoach"
    TASK_NAME = "Taak"
    ACTION_NAME = "Stap"

    def __init__(self):
        self.client = AskDelphiClient()
        self.client.authenticate()
        self.link_list = {}

    def create_source_topics(self, sources):
        topics = topic.fetch_topiclist(self.client)
        self.upload_source_topics(sources, topics)

    def create_link_list(self, json_digicoach, topics):
        bronnen = {}

        tasks = json_digicoach["tasks"]
        for task in tasks:
            t = topic.get_topic_by_title(task["name"], topics)
            bronnen[t["title"]] = t["topicGuid"]

            for step in task["steps"]:
                t = topic.get_topic_by_title(step["name"], topics)
                bronnen[t["title"]] = t["topicGuid"]

        sources = json_digicoach["sources"]
        for source in sources:
            t = topic.get_topic_by_title(source["titel"], topics)
            bronnen[t["title"]] = t["topicGuid"]

        self.link_list = bronnen

    def upload_source_topics(self, sources, topics):
        for source in sources:
            t = topic.get_topic_by_title(source["titel"], topics)
            if t is not None:
                print(f"Gevonden : {t['topicGuid']}, {t['title']}, {t['topicTypeName']}, {source['link']}")
            else:
                topic_type_name = classify_url(source["link"])
                topic_id = topic.upload_topic(self.client, source["titel"], topic_type_name)
                topic_version_id = topic.get_topic_version_id(self.client, topic_id)
                topic_content.add_link_to_topic(self.client, topic_id, topic_version_id, source["link"])
                topic.checkin(self.client, topic_id)
                workflow.publiceer(self.client, topic_id)
                print(f"Niet gevonden : {source['link']} toegevoegd")

    def _create_link(self, description, target_topic_id):
        """Helper die create_link aanroept met client IDs."""
        return create_link(
            description, target_topic_id,
            self.client.tenant_id, self.client.project_id, self.client.acl_entry_id
        )

    def create_voorgedefinieerde_zoekopdracht_topic(self, name):
        topic_id = topic.upload_topic(self.client, name, "Pre-defined search")
        topic_version_id = topic.get_topic_version_id(self.client, topic_id)
        print(f"Created Voorgedefinieerde zoekopdracht topic : {topic_id}")
        return topic_id, topic_version_id

    def create_digicoach(self, name, topic_id_predefined_search, topic_version_id_predefined_search):
        topic_id_digicoach = str(uuid.uuid4())
        topic_type_id = config.get_topic_type_id(self.client, "Digitale Coach Procespagina")
        parent_relation_type_id = relations.get_relation_type_id(
            self.client, topic_id_predefined_search, topic_version_id_predefined_search,
            "Voorgedefinieerde zoekopdracht"
        )
        relations.add_topic_with_relation(
            self.client, topic_id_digicoach, name, topic_type_id,
            topic_id_predefined_search, parent_relation_type_id, topic_version_id_predefined_search
        )
        print(f"Created Digicoach topic : {topic_id_digicoach}")
        topic_version_id_digicoach = topic.get_topic_version_id(self.client, topic_id_digicoach)
        return topic_id_digicoach, topic_version_id_digicoach

    def add_tag(self, topic_id_digicoach, topic_version_id_digicoach, tag):
        relations.add_tag(self.client, topic_id_digicoach, topic_version_id_digicoach, tag)

    def create_task(self, name, topic_id_digicoach, topic_version_id_digicoach):
        topic_id_task = str(uuid.uuid4())
        topic_type_id = config.get_topic_type_id(self.client, "Task")
        parent_relation_type_id = relations.get_relation_type_id(
            self.client, topic_id_digicoach, topic_version_id_digicoach, "Taak"
        )
        relations.add_topic_with_relation(
            self.client, topic_id_task, name, topic_type_id,
            topic_id_digicoach, parent_relation_type_id, topic_version_id_digicoach
        )
        print(f"Created Task topic : {topic_id_task}")
        topic_version_id_task = topic.get_topic_version_id(self.client, topic_id_task)
        return topic_id_task, topic_version_id_task

    def create_step(self, name, topic_id_task, topic_version_id_task):
        topic_id_step = str(uuid.uuid4())
        topic_type_id = config.get_topic_type_id(self.client, "Action")
        parent_relation_type_id = relations.get_relation_type_id(
            self.client, topic_id_task, topic_version_id_task, "Stap"
        )
        relations.add_topic_with_relation(
            self.client, topic_id_step, name, topic_type_id,
            topic_id_task, parent_relation_type_id, topic_version_id_task
        )
        print(f"Created Action topic : {topic_id_step}")
        topic_version_id_step = topic.get_topic_version_id(self.client, topic_id_step)
        return topic_id_step, topic_version_id_step

    def add_sources(self, topic_id, topic_version_id, text, sources):
        topic_id_links = []

        for source in sources:
            if source["titel"] in text:
                topic_id_link = self.link_list[source["titel"]]
                topic_id_links.append(topic_id_link)

        relation_type_id = relations.get_relation_type_id_by_name(
            self.client, topic_id, topic_version_id, "Handleidingen en instructies"
        )

        for topic_id_link in topic_id_links:
            relations.add_relation(self.client, topic_id, topic_version_id, relation_type_id, topic_id_link)
            link_title = keys_by_value(self.link_list, topic_id_link)
            print(f"Externe link : {link_title} toegevoegd onder Handleidingen en instructies")

    def add_source(self, topic_id, topic_version_id, source):
        parent_relation_type_id = relations.get_relation_type_id_by_name(
            self.client, topic_id, topic_version_id, "Handleidingen en instructies"
        )

        topic_id_source = str(uuid.uuid4())
        topic_type_id = config.get_topic_type_id(self.client, "External URL")

        relations.add_topic_with_relation(
            self.client, topic_id_source, source["titel"], topic_type_id,
            topic_id, parent_relation_type_id, topic_version_id
        )

        topic_version_id_source = topic.get_topic_version_id(self.client, topic_id_source)
        topic_content.add_link_to_topic(self.client, topic_id_source, topic_version_id_source, source["link"])

        return topic_id_source, topic_version_id_source

    def add_content_to_topic(self, topic_id, topic_version_id, text):
        topic_content.add_content_to_topic(self.client, topic_id, topic_version_id, text, self.link_list)
