"""
Gedeelde functies: tekst, datums, URLs.
"""
import re
from datetime import datetime


def parse_iso_ts(s):
    """Maakt alle timestamp formaten netjes leesbaar."""
    if not s:
        return None
    s = s.replace("Z", "")
    if "+" in s:
        s = s.split("+", 1)[0]
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def classify_url(url):
    """Classificeer een URL als type bron."""
    url = url.lower()
    if "www.belastingdienst.nl" in url:
        return "External URL"
    elif "connectpeople.belastingdienst.nl" in url:
        return "ConnectPeople"
    else:
        return "External URL"


def is_alleen_url(tekst):
    """Check of de tekst alleen een URL bevat."""
    patroon = r"""^
        (https?:\/\/)?                 # optioneel http/https
        ([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,} # domeinnaam
        (\/\S*)?                       # optioneel pad
    $"""
    return re.match(patroon, tekst.strip(), re.VERBOSE) is not None


def create_link(description, target_topic_id, tenant_id, project_id, acl_entry_id):
    """Bouw een doppio-link HTML element."""
    link = (
        f"\xa0<doppio-link "
        f"target=\"{target_topic_id}\" "
        f"use=\"default\" "
        f"view=\"default\" "
        f"title=\"{description}\" "
        f"thumbnail=\"\" "
        f"link=\"tenant/{tenant_id}/project/{project_id}/acl/{acl_entry_id}/topic/{target_topic_id}/edit\">"
        f"{description}</doppio-link><span>\xa0</span>"
    )
    return link


def hyperlink_html(description, link_list, create_link_fn):
    """Vervang bekende titels in description door doppio-links.

    Args:
        description: De tekst om te doorzoeken.
        link_list: Dict van {titel: topicGuid}.
        create_link_fn: Functie(description, topicGuid) -> HTML link string.
    """
    if not link_list:
        return description

    # titels sorteren lang -> kort
    titles = sorted(link_list.keys(), key=len, reverse=True)

    # Bouw regex met named groups
    parts = []
    for idx, t in enumerate(titles):
        group_name = f"G{idx}"
        parts.append(f"(?P<{group_name}>{re.escape(t)})")

    pattern = re.compile("|".join(parts), re.IGNORECASE)

    def _repl(m):
        matched_text = m.group(0)
        for idx, t in enumerate(titles):
            group_name = f"G{idx}"
            if m.group(group_name):
                topic_guid = link_list[t]
                return create_link_fn(matched_text, topic_guid)
        return matched_text

    return pattern.sub(_repl, description)


def keys_by_value(d, value):
    """Vind alle keys in dict d met de gegeven value."""
    return [k for k, v in d.items() if v == value]


def has_datetime_in_title(title):
    """Checkt of de titel een datetime bevat in het formaat YYYY-MM-DD HH:MM:SS(.microseconds)."""
    TITLE_DATETIME_REGEX = re.compile(r"\b\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\b")
    if not isinstance(title, str):
        return False
    return bool(TITLE_DATETIME_REGEX.search(title))


def filter_topics_with_title_datetime(topics):
    """Retourneert alleen topics waarvoor de title een datetime bevat."""
    if not isinstance(topics, list):
        return []
    return [t for t in topics if isinstance(t, dict) and has_datetime_in_title(t.get("title", ""))]
