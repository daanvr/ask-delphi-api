"""
Topic management: aanmaken, verwijderen, checkin/checkout, opvragen.
"""
from ask_delphi_api import api
from ask_delphi_api import config
from ask_delphi_api.helpers import parse_iso_ts
from datetime import datetime


def get_topic_by_title(title, topics):
    """Zoek topic op titel, geeft het meest recent gewijzigde terug."""
    matching = [t for t in topics if t.get("title") == title]
    if not matching:
        return None
    return max(matching, key=lambda t: t.get("lastModificationDate"))


def fetch_topiclist(client, page_size=100):
    """Haalt alle topics op via paginatie."""
    all_topics = []
    page = 0

    while True:
        resp = api.post_topiclist(client, query="", page=page, page_size=page_size)

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


def filter_between(client, start_str, end_str):
    """Filter topics op basis van timestamp range."""
    start = datetime.fromisoformat(start_str.replace("Z", ""))
    end = datetime.fromisoformat(end_str.replace("Z", ""))

    topics = fetch_topiclist(client)

    selected = []
    for t in topics:
        ts_str = t.get("lastModificationDate")
        ts = parse_iso_ts(ts_str)
        if not ts:
            continue
        if start <= ts <= end:
            selected.append({
                "topicGuid": t.get("topicGuid"),
                "title": t.get("title"),
                "LastModificationDate": ts_str
            })

    selected.sort(key=lambda x: parse_iso_ts(x["LastModificationDate"]))
    return selected


def checkout(client, topic_id):
    """Voer een check-out uit."""
    return api.post_topic_workflowstate_v3(client, topic_id, 1)


def checkin(client, topic_id):
    """Voer een check-in uit."""
    return api.post_topic_workflowstate_v3(client, topic_id, 0)


def get_topic_version_id(client, topic_id):
    """Haal de topicVersionId op."""
    result = api.post_topic_workflowstate(client, topic_id, 1)
    return result["topicVersionId"]


def upload_topic(client, title, type_name):
    """Maak een nieuw topic aan van het opgegeven type. Retourneert topicId."""
    topic_type_id = config.get_topic_type_id(client, type_name)
    result = api.create_topic(client, {
        "topicTitle": title,
        "topicTypeId": topic_type_id
    })
    return result["topicId"]


def delete_topic(client, topic_id, version_id, workflowstage_ids):
    """Verwijder een topic."""
    workflow_data = {
        "workflowActions": {
            "applyWorkflowStageIds": workflowstage_ids,
            "increaseMajorVersionNo": True
        }
    }
    return api.delete_topic(client, topic_id, version_id, workflow_data)


def get_topic_relations(client, topic_id):
    """Haal relaties op voor een topic."""
    return api.get_topic_relations(client, topic_id)
