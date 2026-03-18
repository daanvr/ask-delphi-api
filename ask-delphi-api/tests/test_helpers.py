"""
Tests voor helpers.py — pure logic tests, geen mocking nodig.
"""
from datetime import datetime
from ask_delphi_api.helpers import (
    parse_iso_ts,
    classify_url,
    is_alleen_url,
    create_link,
    hyperlink_html,
    keys_by_value,
    has_datetime_in_title,
    filter_topics_with_title_datetime,
)


# ---------------------------------------------------------------------------
# parse_iso_ts
# ---------------------------------------------------------------------------

def test_parse_iso_ts_basic():
    result = parse_iso_ts("2024-01-15T10:30:00")
    assert result == datetime(2024, 1, 15, 10, 30, 0)


def test_parse_iso_ts_with_z():
    result = parse_iso_ts("2024-01-15T10:30:00Z")
    assert result == datetime(2024, 1, 15, 10, 30, 0)


def test_parse_iso_ts_with_timezone():
    result = parse_iso_ts("2024-01-15T10:30:00+02:00")
    assert result == datetime(2024, 1, 15, 10, 30, 0)


def test_parse_iso_ts_none():
    assert parse_iso_ts(None) is None


def test_parse_iso_ts_empty():
    assert parse_iso_ts("") is None


# ---------------------------------------------------------------------------
# classify_url
# ---------------------------------------------------------------------------

def test_classify_url_belastingdienst():
    assert classify_url("https://www.belastingdienst.nl/page") == "External URL"


def test_classify_url_connectpeople():
    assert classify_url("https://connectpeople.belastingdienst.nl/page") == "ConnectPeople"


def test_classify_url_other():
    assert classify_url("https://example.com") == "External URL"


# ---------------------------------------------------------------------------
# is_alleen_url
# ---------------------------------------------------------------------------

def test_is_alleen_url_true():
    assert is_alleen_url("https://example.com/path") is True


def test_is_alleen_url_false():
    assert is_alleen_url("Dit is geen URL maar tekst") is False


def test_is_alleen_url_bare_domain():
    assert is_alleen_url("example.com") is True


# ---------------------------------------------------------------------------
# create_link
# ---------------------------------------------------------------------------

def test_create_link():
    result = create_link("Mijn Link", "topic-123", "t1", "p1", "a1")
    assert 'target="topic-123"' in result
    assert 'title="Mijn Link"' in result
    assert "tenant/t1/project/p1/acl/a1/topic/topic-123/edit" in result
    assert "doppio-link" in result


# ---------------------------------------------------------------------------
# hyperlink_html
# ---------------------------------------------------------------------------

def test_hyperlink_html_replaces_title():
    link_list = {"Werkproces": "guid-1"}

    def mock_create_link(desc, guid):
        return f"<link>{desc}:{guid}</link>"

    result = hyperlink_html("Zie het Werkproces voor details", link_list, mock_create_link)
    assert "<link>Werkproces:guid-1</link>" in result
    assert "Zie het " in result


def test_hyperlink_html_empty_list():
    result = hyperlink_html("Geen links hier", {}, lambda d, g: "")
    assert result == "Geen links hier"


def test_hyperlink_html_no_match():
    link_list = {"Onbekend": "guid-1"}

    def mock_create_link(desc, guid):
        return f"<link>{desc}</link>"

    result = hyperlink_html("Geen match hier", link_list, mock_create_link)
    assert result == "Geen match hier"


# ---------------------------------------------------------------------------
# keys_by_value
# ---------------------------------------------------------------------------

def test_keys_by_value():
    d = {"a": 1, "b": 2, "c": 1}
    assert sorted(keys_by_value(d, 1)) == ["a", "c"]


def test_keys_by_value_no_match():
    assert keys_by_value({"a": 1}, 99) == []


# ---------------------------------------------------------------------------
# has_datetime_in_title
# ---------------------------------------------------------------------------

def test_has_datetime_in_title_true():
    assert has_datetime_in_title("Topic 2024-01-15 10:30:00 test") is True


def test_has_datetime_in_title_with_microseconds():
    assert has_datetime_in_title("Topic 2024-01-15 10:30:00.123456") is True


def test_has_datetime_in_title_false():
    assert has_datetime_in_title("Gewone titel") is False


def test_has_datetime_in_title_non_string():
    assert has_datetime_in_title(None) is False


# ---------------------------------------------------------------------------
# filter_topics_with_title_datetime
# ---------------------------------------------------------------------------

def test_filter_topics_with_title_datetime():
    topics = [
        {"title": "Topic 2024-01-15 10:30:00"},
        {"title": "Gewone titel"},
        {"title": "Ander topic 2024-02-01 08:00:00.123"},
    ]
    result = filter_topics_with_title_datetime(topics)
    assert len(result) == 2
    assert result[0]["title"] == "Topic 2024-01-15 10:30:00"


def test_filter_topics_with_title_datetime_not_list():
    assert filter_topics_with_title_datetime("niet een lijst") == []
