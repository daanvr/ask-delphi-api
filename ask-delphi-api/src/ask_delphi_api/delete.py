"""
Delete: verwijderen van digicoach structuren.
"""
from ask_delphi_api.client import AskDelphiClient
from ask_delphi_api import topic, relations, workflow
from ask_delphi_api.helpers import has_datetime_in_title, filter_topics_with_title_datetime


class RemoveDigicoach:

    def __init__(self):
        self.client = AskDelphiClient()
        self.client.authenticate()

    def delete_relation(self, topic_id_source, topic_id_target, relation_name):
        """Verwijder een relatie: checkout → resolve → delete → checkin → publiceer."""
        response = None
        try:
            topic.checkout(self.client, topic_id_source)
            source_version_id = topic.get_topic_version_id(self.client, topic_id_source)

            relation_type_id = relations.get_relation_type_id(
                self.client, topic_id_source, source_version_id, relation_name
            )

            response = relations.delete_relation(
                self.client, topic_id_source, source_version_id, topic_id_target, relation_type_id
            )
        except Exception as e:
            print(f"Opruimen van topic relation mislukt: {e}")
        finally:
            try:
                topic.checkin(self.client, topic_id_source)
            finally:
                workflow.publiceer(self.client, topic_id_source)

        return response

    def soft_delete_topic(self, topic_id, workflowstage_ids):
        """Soft delete: checkout → delete → checkin."""
        try:
            topic.checkout(self.client, topic_id)
            version_id = topic.get_topic_version_id(self.client, topic_id)
            response = topic.delete_topic(self.client, topic_id, version_id, workflowstage_ids)
        except Exception as e:
            print(f"Soft delete mislukt: {e}")
            response = {}
        finally:
            topic.checkin(self.client, topic_id)

        return response

    def get_topic_ids(self, items, target_topic_type):
        topic_ids = []
        for d in items:
            if d.get("targetTopicType") == target_topic_type and d.get("targetTopicIsDeleted") is False:
                topic_ids.append(d["targetTopicId"])
        return topic_ids

    def filter_topics(self, topic_type_name):
        """Filter alle topics op topicTypeName."""
        topics = topic.fetch_topiclist(self.client)

        result = []
        for t in topics:
            if not isinstance(t, dict):
                continue
            if t.get("topicTypeName") == topic_type_name:
                result.append({
                    "topicGuid": t.get("topicGuid"),
                    "title": t.get("title"),
                    "lastModificationDate": t.get("lastModificationDate")
                })

        return result

    def delete(self, topic_id_digicoach):
        """Verwijder een digicoach met alle taken en stappen."""
        workflowstage_ids_list = [
            '9d3b3151-b543-4d6f-a9e5-18f4388753e2',
            'ad70aeea-a938-469d-a6fb-493883ae982b',
            '45faa337-2499-4f06-a5c2-c919e4291bb2'
        ]

        response = topic.get_topic_relations(self.client, topic_id_digicoach)

        task_topic_ids = self.get_topic_ids(response['relations'], "Task")

        for task_topic_id in task_topic_ids:
            response = topic.get_topic_relations(self.client, task_topic_id)
            action_topic_ids = self.get_topic_ids(response['relations'], "Action")

            for action_topic_id in action_topic_ids:
                print("Opruimen Digicoach stap plus relatie taak")
                self.delete_relation(task_topic_id, action_topic_id, "Stap")
                self.soft_delete_topic(action_topic_id, workflowstage_ids_list)

            print("Opruimen Digicoach taak plus relatie proces")
            self.delete_relation(topic_id_digicoach, task_topic_id, "Taak")
            self.soft_delete_topic(task_topic_id, workflowstage_ids_list)

        print("Opruimen Digicoach proces")
        self.soft_delete_topic(topic_id_digicoach, workflowstage_ids_list)
