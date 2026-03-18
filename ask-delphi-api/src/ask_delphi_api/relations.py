"""
Relations en tags: relaties tussen topics beheren, tags toevoegen.
"""
from ask_delphi_api import api
from ask_delphi_api.config import CONSTANTS_DIRECTIE, CONSTANTS_KETEN, CONSTANTS_MIDDEL, CONSTANTS_DOCUMENT_TYPE


def get_relation_type_id(client, topic_id, topic_version_id, topic_type_name):
    """Zoek relation type ID op basis van topicTypeName."""
    result = api.get_allowed_relations(client, topic_id, topic_version_id)
    for relation in result["topicAllowedRelations"]:
        if relation["topicTypeName"] == topic_type_name:
            return relation["relationTypeId"]
    return ""


def get_relation_type_id_by_name(client, topic_id, topic_version_id, relation_type_name):
    """Zoek relation type ID op basis van relationTypeName."""
    result = api.get_allowed_relations(client, topic_id, topic_version_id)
    for item in result["topicAllowedRelations"]:
        print(item)
        if item['relationTypeName'] == relation_type_name:
            return item["relationTypeId"]
    return ""


def get_project_tags(client, topic_id, topic_version_id):
    """Haal project tags op, geeft dict {title: tag_data}."""
    response = api.get_editor_tag_model(client, topic_id, topic_version_id)
    return {item["hierarchyNodeTitle"]: item for item in response['data']['projectTags']}


def add_tag(client, topic_id, topic_version_id, tag_data):
    """Voeg een tag toe aan een topic."""
    return api.add_topic_tag(client, topic_id, topic_version_id, tag_data)


def add_tags_to_topic(client, topic_id, topic_version_id, tags, project_tags):
    """Voeg meerdere tags toe aan een topic, met mapping via constanten."""
    for tag in tags:
        for value in tag["values"]:
            if tag["type"] == "Directie":
                value = CONSTANTS_DIRECTIE[value]
            elif tag["type"] == "Keten":
                value = CONSTANTS_KETEN[value]
            elif tag["type"] == "Middel":
                value = CONSTANTS_MIDDEL[value]
            elif tag["type"] == "Document_type":
                value = CONSTANTS_DOCUMENT_TYPE[value]
            tag_data = project_tags[value]
            add_tag(client, topic_id, topic_version_id, tag_data)


def add_relation(client, source_id, source_version_id, relation_type_id, target_id):
    """Voeg een relatie toe."""
    return api.add_topic_relation(client, source_id, source_version_id, relation_type_id, [target_id])


def add_topic_with_relation(client, topic_id, topic_title, topic_type_id, parent_topic_id, parent_relation_type_id, parent_version_id):
    """Maak een topic aan met een relatie naar een parent topic."""
    return api.create_topic(client, {
        "topicId": topic_id,
        "topicTitle": topic_title,
        "topicTypeId": topic_type_id,
        "parentTopicId": parent_topic_id,
        "parentTopicRelationTypeId": parent_relation_type_id,
        "parentTopicVersionId": parent_version_id
    })


def delete_relation(client, source_id, source_version_id, target_id, relation_type_id):
    """Verwijder een relatie."""
    return api.delete_topic_relation(client, source_id, source_version_id, target_id, relation_type_id)
