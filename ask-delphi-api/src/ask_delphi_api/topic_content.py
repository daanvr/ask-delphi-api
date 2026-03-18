"""
Topic content: inhoud wijzigen (body tekst, links).
"""
from ask_delphi_api import api
from ask_delphi_api.helpers import hyperlink_html, create_link


def _find_part(topic_parts, match_key, match_value):
    """Zoek een specifiek part in de topic editor data."""
    groups = topic_parts['topicEditorData']['groups']
    for group in groups:
        for part in group['parts']:
            if part.get(match_key) == match_value:
                return part
    return None


def add_content_to_topic(client, topic_id, topic_version_id, text, link_list=None):
    """Voeg rich text content toe aan het body-part van een topic."""
    content = api.get_topic_parts(client, topic_id)
    body_part = _find_part(content, "partId", "body")

    if link_list:
        def _create_link(description, target_topic_id):
            return create_link(
                description, target_topic_id,
                client.tenant_id, client.project_id, client.acl_entry_id
            )
        text = hyperlink_html(text, link_list, _create_link)

    body_part['editors'][0]['value']['richTextEditor'] = {'value': text}
    api.update_topic_part(client, topic_id, topic_version_id, "body", body_part)


def add_link_to_topic(client, topic_id, topic_version_id, url):
    """Voeg een URL toe aan het link-meta-data part van een topic."""
    content = api.get_topic_parts(client, topic_id)
    link_part = _find_part(content, "defaultLabel", "Link metadata")

    link_part['editors'][0]['value']['string'] = {'markup': None, 'value': url}
    api.update_topic_part(client, topic_id, topic_version_id, "link-meta-data", link_part)
