# Werkplan Generator — Integratie-instructies

## Doel

Voeg een "Werkplan" icoon/knop toe aan elke boring in het HDD platform.
Het werkplan kan altijd gegenereerd worden (ook als niet alle data compleet is — ontbrekende velden worden als rode placeholders getoond). Output: Word (.docx) download.

---

## Wat er al staat

De werkplan generator is volledig gebouwd en werkend. Deze bestanden zijn nieuw/gewijzigd:

### Nieuwe bestanden
| Bestand | Functie |
|---|---|
| `app/documents/werkplan_generator.py` | Genereert de .docx — haalt alles uit DB |
| `app/ai_assist/werkplan_teksten.py` | Claude AI tekstgeneratie (inleiding, locatie, kwel) |
| `app/templates/documents/werkplan_form.html` | Formulier + afbeelding-uploads |

### Gewijzigde bestanden
| Bestand | Wijziging |
|---|---|
| `app/order/models.py` | Nieuw model `WerkplanAfbeelding` + relatie op `Boring` |
| `app/documents/router.py` | Werkplan GET/POST routes toegevoegd |
| `app/order/router.py` | Afbeelding upload/delete routes + import `WerkplanAfbeelding` |
| `app/templates/order/boring_detail.html` | "Werkplan genereren" knop toegevoegd |
| `requirements.txt` | `python-docx==1.2.0` en `anthropic>=0.40.0` toegevoegd |

### Database
Nieuwe tabel `werkplan_afbeeldingen` — wordt aangemaakt met:
```python
from app.order.models import WerkplanAfbeelding
WerkplanAfbeelding.__table__.create(engine, checkfirst=True)
```
Of via Alembic migration.

---

## Te integreren: Werkplan-icoon per boring

### Waar: Order detail pagina (`app/templates/order/detail.html`)

In de boringen-tabel staat per boring een rij met kolom "Acties" die nu 3 knoppen heeft: Details, Trace, Brondata.

**Voeg een 4e knop toe** — "Werkplan":

```html
<!-- In de boringen tabel, bij de acties kolom per boring -->
<a href="/api/v1/orders/{{ order.id }}/boringen/{{ b.volgnummer }}/werkplan"
   class="btn btn-sm btn-primary"
   title="Werkplan genereren">
  Werkplan
</a>
```

Dit linkt naar het werkplan-formulier waar de gebruiker:
1. Opties invult (auteur, hoofdaannemer, revisie, etc.)
2. Optioneel afbeeldingen uploadt (luchtfoto, topotijdreis, KLIC screenshot)
3. Optioneel AI-tekstgeneratie aanzet
4. Op "Genereer Werkplan (.docx)" klikt → download start

### Alternatief: Direct download (zonder formulier)

Als je een directe download wilt zonder formulier (met standaard-opties), maak dan een extra route:

```python
# In app/documents/router.py
@router.get("/orders/{order_id}/boringen/{volgnr}/werkplan/download")
def werkplan_direct_download(
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Direct downloaden met standaard opties."""
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    docx_bytes = generate_werkplan(
        order=order,
        boring=boring,
        gebruik_ai=True,  # AI standaard aan
    )

    locatie = order.locatie or "locatie"
    boring_naam = boring.naam or f"HDD{boring.volgnummer}"
    filename = f"{order.ordernummer} {boring_naam} Werkplan - {locatie}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

---

## API Routes overzicht

| Method | Route | Functie |
|---|---|---|
| GET | `/api/v1/orders/{id}/boringen/{nr}/werkplan` | Formulier pagina |
| POST | `/api/v1/orders/{id}/boringen/{nr}/werkplan` | Genereer + download .docx |
| POST | `/orders/{id}/boringen/{nr}/werkplan-afbeelding` | Upload afbeelding |
| POST | `/orders/{id}/boringen/{nr}/werkplan-afbeelding/{afb_id}/delete` | Verwijder afbeelding |

---

## Dataflow

```
Boring (DB)
  ├── Order: ordernummer, locatie, opdrachtgever, vergunning
  ├── Boring: materiaal, SDR, De_mm, medium, Dg_mm, hoeken
  ├── TracePunt[]: RD-coordinaten → tabel in werkplan
  ├── Doorsnede[]: bodemopbouw → context voor AI
  ├── Berekening: Ttot_N → intrekkracht + CKB categorie
  ├── MaaiveldOverride: NAP waarden
  ├── KLIC: leidingen/beheerders info
  └── WerkplanAfbeelding[]: uploads per categorie
        ├── luchtfoto → H2.1
        ├── topotijdreis_1/2/3 → H2.2
        ├── klic → H2.3
        └── rws → H2.3 (alleen bij vergunning=R)
                    │
                    ▼
          Claude AI (optioneel, Haiku 4.5)
            ├── genereer_inleiding()
            ├── genereer_locatie_beschrijving()
            └── genereer_kwel_beoordeling()
                    │
                    ▼
            werkplan_generator.py
                    │
                    ▼
              .docx download
```

---

## Werkplan structuur (wat er gegenereerd wordt)

| Hoofdstuk | Inhoud | Databron |
|---|---|---|
| Voorpagina | Titel, locatie, opdrachtgever, revisietabel | Order |
| 1. Inleiding | Projectbeschrijving | AI of template |
| 2.1 Locatie | Beschrijving + luchtfoto | AI + afbeelding |
| 2.2 Historie | Topotijdreis screenshots + conclusie | Afbeeldingen |
| 2.3 Infrastructuur | KLIC screenshot + K&L analyse, evt. RWS | Afbeeldingen + Order.vergunning |
| 3. Ontwerp | Buisspecificaties, boorprofiel | Boring (materiaal, SDR, De, medium) |
| 3.2 Metingen | Boorkop, bentoniet, boorspoelparameters | Standaardtekst |
| 3.2.4 RD-coord | Coordinaten tabel | TracePunt[] |
| 4. Berekeningen | Sterkte, intrekkracht, boorspoeldruk | Berekening.Ttot_N |
| 5. Kwel | Beoordeling | AI of template |
| 6. Uitvoering | CKB-categorie, personeel, planning | Auto (op basis van Ttot_N) |
| Bijlagen A-G | Placeholders | — |

---

## Vereisten

```
python-docx==1.2.0    # Word generatie
anthropic>=0.40.0      # Claude AI (optioneel — werkt ook zonder)
```

`ANTHROPIC_API_KEY` moet in `.env` staan voor AI-functionaliteit. Zonder key werkt alles, maar dan krijg je template-teksten in plaats van AI-gegenereerde teksten.

---

## Snel testen

```python
# In Python shell (.venv/bin/python)
from app.documents.werkplan_generator import generate_werkplan
from app.core.database import get_db, engine
from sqlalchemy.orm import Session
from app.order.models import Order, Boring

db = Session(engine)
order = db.query(Order).first()
boring = order.boringen[0]

result = generate_werkplan(order, boring, gebruik_ai=False)
with open("test_werkplan.docx", "wb") as f:
    f.write(result)
print(f"Gegenereerd: {len(result)} bytes")
```
