# Ask Delphi API Python Client

Een simpele Python client om te communiceren met de Ask Delphi Content API.

## Snelstart

### Vereisten
- Python 3.8 of hoger
- UV package manager (aanbevolen) of pip

### Windows

```powershell
# 1. Maak virtual environment
uv venv

# 2. Activeer virtual environment
.venv\Scripts\activate

# 3. Installeer dependencies
uv pip install -r requirements.txt

# 4. Kopieer credentials template
copy .env.example .env
# Open .env in een editor en vul je waarden in

# 5. Test de connectie
python test_api.py
```

### macOS / Linux

```bash
# 1. Maak virtual environment
uv venv

# 2. Activeer virtual environment
source .venv/bin/activate

# 3. Installeer dependencies
uv pip install -r requirements.txt

# 4. Kopieer credentials template
cp .env.example .env
# Open .env in een editor en vul je waarden in

# 5. Test de connectie
python test_api.py
```

### Alternatief: met pip (zonder UV)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Credentials Ophalen

Je hebt 4 dingen nodig om de API te gebruiken:

### 1. Tenant ID, Project ID, ACL Entry ID

Deze vind je in de URL wanneer je ingelogd bent in de CMS:

```
https://xxx.askdelphi.com/cms/tenant/87b664f3-db62-4f9d-a008-c7f5f26928eb/project/c7018a99-8cb7-45f1-b2d4-00332ef9ecf5/acl/7d712c17-c988-4d6a-9dd0-644cc6f562a2/...
                                    └──────────────── TENANT ID ────────────────┘        └──────────────── PROJECT ID ────────────────┘     └──────────────── ACL ENTRY ID ───────────────┘
```

### 2. Portal Code

1. Ga naar je publicatie in AskDelphi
2. Klik op de **Mobile** tab aan de rechterkant
3. Je ziet een "Session code" - dit is je portal code
4. Deze code is eenmalig en wordt omgewisseld voor tokens

**Let op:** De portal code is tijdelijk. Na eerste gebruik wordt deze omgewisseld voor tokens die automatisch worden opgeslagen.

## Hoe Authenticatie Werkt

```
Portal Code  ──GET──>  portal.askdelphi.com/api/session/registration
                                    │
                                    v
                      { accessToken, refreshToken, url }
                                    │
                                    v
Access Token ──GET──>  {url}/api/token/EditingApiToken
                                    │
                                    v
                            API Token (JWT)
                            (1 uur geldig)
```

De client handelt dit automatisch af:
- Eerste keer: portal code → tokens → API token
- Daarna: tokens worden lokaal opgeslagen en hergebruikt
- Token verlopen? Wordt automatisch ververst

## Gebruik

### Basis Voorbeeld

```python
from askdelphi_client import AskDelphiClient

# Client initialiseren
client = AskDelphiClient()

# Authenticeren (eerste keer met portal code)
client.authenticate()

# Topic types ophalen
design = client.get_content_design()
for topic_type in design['topicTypes'][:5]:
    print(f"- {topic_type['title']}")

# Topic aanmaken
topic = client.create_topic(
    title="Mijn Test Topic",
    topic_type_id="guid-van-topic-type"
)
print(f"Topic aangemaakt: {topic['topicId']}")
```

### Alle Functies

| Functie | Beschrijving |
|---------|--------------|
| `authenticate()` | Authenticeer met portal code of bestaande tokens |
| `get_content_design()` | Haal alle topic types en relaties op |
| `search_topics(query, filters)` | Zoek topics |
| `create_topic(title, type_id)` | Maak nieuw topic |
| `get_topic_parts(topic_id, version_id)` | Haal content van topic op |
| `update_topic_part(...)` | Update content van topic |
| `checkout_topic(topic_id)` | Check topic uit om te bewerken |
| `checkin_topic(...)` | Check topic weer in |

## API Endpoints

De client praat met deze servers:

| Server | URL | Doel |
|--------|-----|------|
| Portal | `https://portal.askdelphi.com` | Authenticatie |
| API | `https://edit.api.askdelphi.com` | Content operaties |

Volledige API documentatie: https://edit.api.askdelphi.com/swagger/index.html

## Veiligheid

**BELANGRIJK:**
- Commit NOOIT je `.env` bestand
- De `.gitignore` is al geconfigureerd om `.env` te negeren
- Tokens worden lokaal opgeslagen in `.askdelphi_tokens.json` (ook genegeerd)
- Deel je portal code niet - deze geeft toegang tot je project

## Troubleshooting

### "Invalid portal code"
- De portal code is eenmalig. Haal een nieuwe op uit de Mobile tab.

### "Token expired"
- De client zou dit automatisch moeten afhandelen
- Als het blijft falen, verwijder `.askdelphi_tokens.json` en haal nieuwe portal code op

### "403 Forbidden"
- Check of je ACL Entry ID correct is
- Check of je gebruiker rechten heeft op het project

## Meer Informatie

- [Swagger API Docs](https://edit.api.askdelphi.com/swagger/index.html)
- [C# Reference Implementation](https://github.com/askdelphibv/askdelphi-content-builder)
