# Ask Delphi API Python Client

Een Python client om te communiceren met de Ask Delphi Content API, inclusief scripts om content te downloaden en uploaden.

## Snelstart

### Vereisten
- Python 3.8 of hoger
- UV package manager (aanbevolen) of pip

### Installatie

**Windows (PowerShell)**
```powershell
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
copy .env.example .env
```

**macOS / Linux**
```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
```

### Credentials Instellen

Open `.env` en vul je gegevens in. **Makkelijkste optie:** plak gewoon de URL uit je browser:

```env
# Plak een URL uit de AskDelphi CMS (tenant/project/acl worden automatisch geparsed)
ASKDELPHI_CMS_URL=https://xxx.askdelphi.com/cms/tenant/87b664f3-.../project/c7018a99-.../acl/7d712c17-.../...

# Portal code uit de Mobile tab van je publicatie (eenmalig gebruik!)
ASKDELPHI_PORTAL_CODE=ABC123-XYZ789
```

### Test de connectie

```bash
python test_api.py
```

---

## Content Download & Upload Scripts

### Alle content downloaden

Download alle topics en content naar een JSON bestand:

```bash
python download_content.py
```

**Opties:**
```bash
python download_content.py -o backup.json      # Specifieke bestandsnaam
python download_content.py -w 20               # 20 parallelle downloads (sneller)
python download_content.py -w 1                # Sequentieel (1 tegelijk)
python download_content.py --no-parts          # Alleen metadata (snelst)
python download_content.py --verbose           # Gedetailleerde output
```

Standaard worden **10 topics parallel** gedownload. Verhoog `-w` voor meer snelheid.

**Output:** `content_export_YYYYMMDD_HHMMSS.json` met alle topics, content en metadata.

### Wijzigingen uploaden

Upload wijzigingen van een lokaal JSON bestand naar het platform:

```bash
# EERST: Bekijk wat er zou veranderen (dry-run)
python upload_content.py content_export.json --dry-run

# DAN: Upload de wijzigingen
python upload_content.py content_export.json
```

**Opties:**
```bash
python upload_content.py data.json --dry-run              # Alleen tonen, niet uploaden
python upload_content.py data.json --original backup.json # Vergelijk met specifiek bestand
python upload_content.py data.json --no-backup            # Geen backup maken
python upload_content.py data.json --force                # Geen bevestiging vragen
```

### Typische Workflow

```bash
# 1. Download huidige content
python download_content.py -o content.json

# 2. Maak een backup
cp content.json content_backup.json

# 3. Bewerk content.json in je favoriete editor
#    - Wijzig topic titles
#    - Pas content aan in de "parts" sectie
#    - etc.

# 4. Bekijk wat er veranderd is
python upload_content.py content.json --original content_backup.json --dry-run

# 5. Upload de wijzigingen
python upload_content.py content.json --original content_backup.json
```

### JSON Structuur

Het geëxporteerde JSON bestand heeft deze structuur:

```json
{
  "_metadata": {
    "exported_at": "2025-01-15T14:30:00Z",
    "topic_count": 507
  },
  "content_design": {
    "topic_types": [...],
    "relations": [...]
  },
  "topics": {
    "topic-uuid-1": {
      "id": "topic-uuid-1",
      "title": "Mijn Topic",
      "topic_type_title": "Procedure",
      "parts": {
        "part-id": {
          "name": "Body",
          "type": "richtext",
          "content": "<p>De content...</p>"
        }
      }
    }
  }
}
```

---

## Client API Gebruik

### Basis Voorbeeld

```python
from askdelphi_client import AskDelphiClient

# Client initialiseren (leest credentials uit .env)
client = AskDelphiClient()

# Authenticeren
client.authenticate()

# Topic types ophalen
design = client.get_content_design()
for topic_type in design['topicTypes'][:5]:
    print(f"- {topic_type['title']}")

# Alle topics ophalen
topics = client.get_all_topics()
print(f"Totaal: {len(topics)} topics")

# Topic aanmaken
topic = client.create_topic(
    title="Mijn Test Topic",
    topic_type_id="guid-van-topic-type"
)
```

### Beschikbare Functies

| Functie | Beschrijving |
|---------|--------------|
| `authenticate()` | Authenticeer met portal code of bestaande tokens |
| `get_content_design()` | Haal alle topic types en relaties op |
| `get_all_topics()` | Haal alle topics op (met automatische pagination) |
| `search_topics(query, filters)` | Zoek topics |
| `create_topic(title, type_id)` | Maak nieuw topic |
| `get_topic_parts(topic_id, version_id)` | Haal content van topic op |
| `update_topic_part(...)` | Update content van topic |
| `checkout_topic(topic_id)` | Check topic uit om te bewerken |
| `checkin_topic(...)` | Check topic weer in |
| `is_topic_checked_out(topic_id)` | Check of topic uitgecheckt is |
| `cancel_checkout(...)` | Annuleer checkout |

---

## Credentials Ophalen

### Optie 1: CMS URL (makkelijkst)

Kopieer een URL uit je browser wanneer je in de AskDelphi CMS bent:
```
https://xxx.askdelphi.com/cms/tenant/{TENANT_ID}/project/{PROJECT_ID}/acl/{ACL_ENTRY_ID}/...
```

Plak deze in `.env` als `ASKDELPHI_CMS_URL` - de IDs worden automatisch geparsed.

### Optie 2: Losse IDs

Je kunt ook de IDs apart invullen:
```env
ASKDELPHI_TENANT_ID=87b664f3-db62-4f9d-a008-c7f5f26928eb
ASKDELPHI_PROJECT_ID=c7018a99-8cb7-45f1-b2d4-00332ef9ecf5
ASKDELPHI_ACL_ENTRY_ID=7d712c17-c988-4d6a-9dd0-644cc6f562a2
```

### Portal Code

1. Ga naar je publicatie in AskDelphi CMS
2. Klik op de **Mobile** tab aan de rechterkant
3. Kopieer de "Session code" (format: `ABC123-XYZ789`)

**Let op:** Portal codes zijn **EENMALIG**! Na eerste gebruik worden ze omgewisseld voor tokens die lokaal worden opgeslagen.

---

## Veiligheid

- Commit **NOOIT** je `.env` bestand
- Tokens worden opgeslagen in `.askdelphi_tokens.json` (genegeerd door git)
- Content exports worden ook genegeerd (`content_export_*.json`, `backup_*.json`)
- Deel je portal code niet - deze geeft toegang tot je project

---

## Troubleshooting

### "401 Unauthorized" bij portal code
- Portal codes zijn **EENMALIG**! Haal een nieuwe op via de Mobile tab.

### "0 topics" bij download
- Check `askdelphi_debug.log` voor de API response
- Zorg dat je de juiste ACL Entry ID hebt

### "Token expired"
- Verwijder `.askdelphi_tokens.json` en haal een nieuwe portal code op

### Debugging
Bij problemen wordt automatisch een debug log aangemaakt:
```
askdelphi_debug.log
```

---

## API Endpoints

| Server | URL | Doel |
|--------|-----|------|
| Portal | `https://portal.askdelphi.com` | Authenticatie |
| API | `https://edit.api.askdelphi.com` | Content operaties |

Volledige API documentatie: https://edit.api.askdelphi.com/swagger/index.html

---

## Meer Informatie

- [Swagger API Docs](https://edit.api.askdelphi.com/swagger/index.html)
- [C# Reference Implementation](https://github.com/askdelphibv/askdelphi-content-builder)
