
from ask_delphi_api.authentication import AskDelphiClient
from ask_delphi_api.project import Project
from ask_delphi_api.topictools import TopicTools
from ask_delphi_api.relation import Relation
from ask_delphi_api.workflow import Workflow
import re

class RemoveDigicoach:

    def __init__(self):

        self.client = AskDelphiClient()
        self.client.authenticate()   # pakt automatisch portal code uit .env
        self.workflow = Workflow(self.client)
        self.project = Project(self.client)
        self.topic = TopicTools(self.client, self.project)
        self.relation = Relation(self.client)

    def delete_relation(self, topic_id_source: str, topic_id_target: str, relation_name: str):
        """
        Verwijder een relatie van source → target van het type `relation_name`.
        Doet: checkout → resolve relation_type_id → delete → checkin → publiceer.
        """
        response = None
        try:
            self.topic.checkout(topic_id_source)
            source_version_id = self.topic.get_topicVersionId(topic_id_source)

            relation_type_id = self.relation.get_relation_type_id(
                topic_id_source, source_version_id, relation_name
            )

            response = self.relation._delete_topic_relation(
                topic_id_source, source_version_id, topic_id_target, relation_type_id
            )

        except Exception as e:
            print(f"Opruimen van topic relation mislukt: {e}")
        finally:
            try:
                self.topic.checkin(topic_id_source)
            finally:
                self.workflow.publiceer(topic_id_source)

        return response

    def soft_delete_topic(self, topic_id: str,  workflowstage_ids: list):
        """Soft delete: checkout → delete → checkin."""
        try:
            self.topic.checkout(topic_id)
            version_id = self.topic.get_topicVersionId(topic_id)
            response = self.topic.delete_topic(topic_id, version_id, workflowstage_ids)
        except Exception as e:
            print(f"Soft delete mislukt: {e}")
            response = {}
        finally:
            self.topic.checkin(topic_id)

        return response

    def get_topic_ids(self, items: list, targetTopicType: str):
        topic_ids =[]
        for d in items:
            if d.get("targetTopicType") == targetTopicType and d.get("targetTopicIsDeleted") is False :
                topic_ids.append(d["targetTopicId"])
                # print(f"{d['targetTopicName']}, {d["targetTopicId"]}")
        return topic_ids

    def has_datetime_in_title(self, title: str) -> bool:
        # Regex: YYYY-MM-DD HH:MM:SS of met microseconden
        TITLE_DATETIME_REGEX = re.compile(r"\b\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\b")
        
        """Checkt of de titel een datetime bevat in het formaat YYYY-MM-DD HH:MM:SS(.microseconds)."""
        if not isinstance(title, str):
            return False
        
        return bool(TITLE_DATETIME_REGEX.search(title))

    def filter_topics_with_title_datetime(self, topics: list[dict]) -> list[dict]:
        """
        Retourneert alleen die topics waarvoor de 'title' een datetime bevat.
        Laat verder de originele dicts intact.
        """
        if not isinstance(topics, list):
            return []
        return [t for t in topics if isinstance(t, dict) and self.has_datetime_in_title(t.get("title", ""))]

    def filter_topics(self, topicTypeName: str):
        """
        Filtert alle topics op topicTypeName
        en geeft een lijst met dicts terug met alleen topicGuid, title en lastModificationDate.
        """

        topics = self.topic.fetch_topiclist()

        result = []

        for topic in topics:
            if not isinstance(topic, dict):
                continue

            if topic.get("topicTypeName") == topicTypeName:
                result.append({
                    "topicGuid": topic.get("topicGuid"),
                    "title": topic.get("title"),
                    "lastModificationDate": topic.get("lastModificationDate")
                })

        return result

    def delete(self, topic_id_digicoach: str):
        """
        Verwijder een digicoach.
        Doet: softdelete relaties, taken, stappen en digicoach proces.
        """

        # Ophalen workflowstage_ids
        # workflowstage_ids = get_workflowstate_ids()
        # workflowstage_ids_list = list(workflowstage_ids.values())
        # print(f"workflowstage_ids_list : {workflowstage_ids_list}")

        # Ophalen van workflowstage ids gaat soms niet goed, voor nuu een lijstje met ids
        workflowstage_ids_list = [
            '9d3b3151-b543-4d6f-a9e5-18f4388753e2', 
            'ad70aeea-a938-469d-a6fb-493883ae982b', 
            '45faa337-2499-4f06-a5c2-c919e4291bb2']

        response = self.topic.get_topic_relation(topic_id_digicoach)

        # Ophalen topic ids taken
        task_topic_ids = self.get_topic_ids(response['relations'], "Task")

        for task_topic_id in task_topic_ids:

            # Ophalen topic ids van de stappen
            response = self.topic.get_topic_relation(task_topic_id)
            action_topic_ids = self.get_topic_ids(response['relations'], "Action")

            # Verwijder stap topics en relations met de taken
            for action_topic_id in action_topic_ids:
                self.delete_relation(task_topic_id, action_topic_id, "Stap")
                self.soft_delete_topic(action_topic_id, workflowstage_ids_list)

            # Verwijder taak topic en relation met de digicoach
            self.delete_relation(topic_id_digicoach, task_topic_id, "Taak")
            self.soft_delete_topic(task_topic_id, workflowstage_ids_list)

        response = self.soft_delete_topic(topic_id_digicoach, workflowstage_ids_list)