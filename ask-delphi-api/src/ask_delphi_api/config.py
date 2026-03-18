"""
IDs, constanten en project-configuratie.
"""
from ask_delphi_api import api

# ---------------------------------------------------------------------------
# Tag-waarde mappings
# ---------------------------------------------------------------------------

CONSTANTS_AFKORTING = {
    "IH, IB"                : "IH, IB",
    "INV"                   : "INV",
    "KI&S"                  : "KI&S",
    "LH"                    : "LH",
    "MRB, BPM"              : "MRB, BPM",
    "OB"                    : "OB",
    "S&E"                   : "S&E",
    "VPB"                   : "VPB"
}

CONSTANTS_DIRECTIE = {
    "CAP"                   : "CAP (Centrale Administratieve Processen)",
    "CD Communicatie"       : "CD Communicatie",
    "CD C&F"                : "CD Control en Financiën",
    "CD DF&A"               : "CD Datafundamenten en Analytics",
    "CD FJZ"                : "CD Fiscale en Juridische zaken",
    "CD I&S"                : "CD Innovatie en Strategie",
    "CD IV&D"               : "Organisatieonderdelen, CD IV en Databeheersing",
    "CD Uitvoerings en handhavingsbeleid" : "CD Uitvoerings- en Handhavingsbeleid",
    "CD Vaktechniek"        : "CD Vaktechniek",
    "Dienst Douane"         : "Dienst Douane",
    "Dienst Toeslagen"      : "Dienst Toeslagen",
    "O&P"                   : "Directie O en P",
    "FIOD"                  : "FIOD (Fiscale Inlichtingen en Opsporingsdienst)",
    "GO"                    : "GO (Grote Ondernemingen)",
    "IV"                    : "IV (Informatievoorziening)",
    "KI&S"                  : "KIenS (Klantinteractie en Services)",
    "MKB"                   : "MKB (Midden- en Kleinbedrijf)",
    "Medezeggenschap"       : "Medezeggenschap",
    "Min Fin"               : "Ministerie van Financiën",
    "Particulieren"         : "P (Particulieren)",
    "CFD"                   : "SSO CFD (Centrum voor Facilitaire Dienstverlening)",
    "F&MI"                  : "SSO F en MI (Financieel en Managementinformatie)"
}

CONSTANTS_DOCUMENT_TYPE = {
    "Digitale coach"        : "Digitale coach",
    "Proces"                : "Proces",
    "Taak"                  : "Taak",
    "Stap"                  : "Stap",
    "Ondersteunende kennis" : "Ondersteunende kennis",
    "Applicatie"            : "Applicatie",
    "Opleidingen"           : "Opleidingen",
    "Sjablonen en tools"    : "Sjablonen en tools",
    "Vakliteratuur"         : "Vakliteratuur",
    "Voorbeelden"           : "Voorbeelden",
    "Video"                 : "Video"
}

CONSTANTS_KENNIS_DOMEIN = {
    "Burgerlijk recht"      : "Burgerlijk recht",
    "Controletechniek"      : "Controletechniek",
    "Formeel recht"         : "Formeel recht",
    "Toeslagen"             : "Toeslagen"
}

CONSTANTS_MIDDEL = {
    "Accijns"                   : "Accijns",
    "Belastingen op personenauto's motorrijwielers" : "Belastingen op personenauto's motorrijwielen",
    "Dividendbelasting"         : "Dividendbelasting",
    "Erfbelasting"              : "Erfbelasting",
    "Huurtoeslag"               : "Huurtoeslag",
    "Inkomensheffing"           : "Inkomensheffing",
    "Kansspelbelasting"         : "Kansspelbelasting",
    "Kindertoeslag"             : "Kindertoeslag",
    "Loonheffingen"             : "Loonheffingen",
    "Milieubelasting"           : "Milieubelasting",
    "Motorrijtuigenbelasting"   : "Motorrijtuigenbelasting",
    "Omzetbelasting"            : "Omzetbelasting",
    "Overdrachtsbelasting"      : "Overdrachtsbelasting",
    "Overige middelen"          : "Overige middelen",
    "Schenkbelasting"           : "Schenkbelasting",
    "Vermogensbelasting"        : "Vermogensbelasting",
    "Vennootschapsbelasting"    : "Vennootschapsbelasting",
    "Zorgtoeslag"               : "Zorgtoeslag"
}

CONSTANTS_KETEN = {
    "Aangifte"                      : "Aangifte",
    "Aanslag"                       : "Aanslag",
    "Bezwaar, beroep en klachten"   : "Bezwaar, beroep en klachten",
    "Controle en toezicht"          : "Controle en toezicht",
    "Gegevens"                      : "Gegevens",
    "Generiek kantoor en Toezicht"  : "Generiek kantoor en Toezicht",
    "Inning en betalingsverkeer"    : "Inning en betalingsverkeer",
    "Interactie"                    : "Interactie"
}


# ---------------------------------------------------------------------------
# Project configuratie functies
# ---------------------------------------------------------------------------

def get_topic_types(client):
    """Haalt de beschikbare topictype mapping op (title → key)."""
    response = api.get_content_design(client)
    contentdesign = response.get("response", response)
    topic_types = contentdesign.get("topicTypes", [])

    topic_type_map = {}
    for tt in topic_types:
        topic_type_map[tt.get("title")] = tt.get("key")

    return topic_type_map


def get_topic_type_id(client, topic_type_name):
    """Haalt de topictype ID op voor een gegeven naam."""
    topic_type_map = get_topic_types(client)
    topic_type_id = topic_type_map.get(topic_type_name)

    if topic_type_id is None:
        raise ValueError(
            f"Unknown topic type: {topic_type_name}",
            f"Available types: {list(topic_type_map.keys())}")

    return topic_type_id
